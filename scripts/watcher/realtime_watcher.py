#!/usr/bin/env python3
"""
Real-time watcher daemon for OpenClaw session files.
Monitors agent session directories and stores conversation turns to Qdrant.
Based on TrueRecall Base architecture (https://gitlab.com/mdkrush/openclaw-true-recall-base)

Usage:
    python3 realtime_watcher.py                          # Watch with defaults
    python3 realtime_watcher.py --sessions-dir /path     # Custom sessions dir
    python3 realtime_watcher.py --create-collection      # Create Qdrant collection first
"""
import os
import sys
import json
import time
import hashlib
import uuid
import logging
import argparse
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

import urllib.request
import urllib.parse
import urllib.error

# Configuration via environment variables with defaults
QDRANT_URL = os.getenv("QDRANT_URL", os.environ.get("QDRANT_URL", "http://localhost:6333"))
OLLAMA_URL = os.getenv("OLLAMA_URL", os.environ.get("OLLAMA_URL", "http://localhost:11434"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "snowflake-arctic-embed2")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "memories_tr")
EMBEDDING_DIM = 1024  # snowflake-arctic-embed2 dimension
LOG_FILE = os.getenv("WATCHER_LOG", "")  # empty = stdout only

# Configure logging
log_handlers = [logging.StreamHandler(sys.stdout)]
if LOG_FILE:
    log_handlers.append(logging.FileHandler(LOG_FILE))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=log_handlers
)
logger = logging.getLogger(__name__)

# Persistent state for tracking file positions
STATE_FILE = os.getenv("WATCHER_STATE", os.path.expanduser("~/.openclaw/.watcher_state.json"))


def load_state() -> dict:
    """Load last processed positions from disk."""
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load state: {e}")
    return {}


def save_state(state: dict):
    """Save last processed positions to disk."""
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f)
    except Exception as e:
        logger.warning(f"Could not save state: {e}")


def get_agent_id_from_path(file_path: str) -> str:
    """Extract agent_id from path like: .openclaw/agents/chief-callie/sessions/..."""
    try:
        parts = Path(file_path).parts
        # Look for "agents" in path (original), or infer from /data/agents or /sessions layout
        # Pattern: .../agents/<agent_id>/sessions/<file>.jsonl
        # OR: /data/agents/<agent_id>/sessions/<file>.jsonl
        for marker in ("agents",):
            if marker in parts:
                agent_idx = parts.index(marker) + 1
                return parts[agent_idx]
        # Fallback: look for a "sessions" directory and take the parent
        for i, part in enumerate(parts):
            if part == "sessions" and i > 0:
                return parts[i - 1]
        raise ValueError("No agent marker found")
    except (ValueError, IndexError):
        logger.warning(f"Could not extract agent_id from path: {file_path}")
        return "unknown"


def clean_text(text: str) -> str:
    """Clean text by removing markdown formatting."""
    if not isinstance(text, str):
        return ""

    # Remove code blocks first (preserves content description)
    text = re.sub(r'```[\s\S]*?```', '[code]', text)

    # Remove markdown tables
    text = re.sub(r'^\|.*\|$', '', text, flags=re.MULTILINE)

    # Remove bold and italic markers
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)

    # Remove inline code
    text = re.sub(r'`(.*?)`', r'\1', text)

    # Remove headers
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

    # Remove multiple consecutive whitespace
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def extract_text_content(content) -> str:
    """Extract text from OpenClaw content (can be string or list of blocks)."""
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        texts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    texts.append(block.get("text", ""))
                elif block.get("type") == "toolCall":
                    # Include tool name for context but skip arguments
                    tool_name = block.get("name", "unknown")
                    texts.append(f"[tool: {tool_name}]")
                elif block.get("type") == "toolResult":
                    # Skip tool results — too noisy
                    pass
            elif isinstance(block, str):
                texts.append(block)
        return " ".join(texts)

    return str(content) if content else ""


def get_embedding(text: str) -> Optional[list]:
    """Generate embedding using Ollama on DS9."""
    if not text or len(text.strip()) < 10:
        return None

    # Try up to 2 times with backoff
    for attempt in range(2):
        try:
            req_data = json.dumps({"model": EMBEDDING_MODEL, "prompt": text[:8000]}).encode()
            req = urllib.request.Request(
                f"{OLLAMA_URL}/api/embeddings",
                data=req_data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                if resp.status != 200:
                    logger.warning(f"Embedding request failed with status {resp.status} (attempt {attempt + 1})")
                    if attempt < 1:  # If not the last attempt, wait before retry
                        time.sleep(5)
                    continue
                result = json.loads(resp.read().decode())
            embedding = result.get("embedding")
            if embedding and len(embedding) == EMBEDDING_DIM:
                return embedding
            logger.warning(f"Unexpected embedding dimension: {len(embedding) if embedding else 0} (attempt {attempt + 1})")
            if attempt < 1:  # If not the last attempt, wait before retry
                time.sleep(5)
            continue
        except Exception as e:
            logger.warning(f"Failed to get embedding (attempt {attempt + 1}): {e}")
            if attempt < 1:  # If not the last attempt, wait before retry
                time.sleep(5)
            continue
    
    # If we get here, all attempts failed
    logger.error("Failed to get embedding after 2 attempts")
    return None


def generate_point_id(content: str, timestamp: str, agent_id: str) -> str:
    """Generate a deterministic UUID for Qdrant point (for deduplication)."""
    unique_str = f"{agent_id}:{timestamp}:{content[:200]}"
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, unique_str))


def create_collection():
    """Create the memories_tr collection in Qdrant if it doesn't exist."""
    try:
        # Check if collection exists
        req = urllib.request.Request(f"{QDRANT_URL}/collections/{COLLECTION_NAME}")
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                result = json.loads(resp.read().decode())
                logger.info(f"Collection '{COLLECTION_NAME}' already exists")
                count = result.get("result", {}).get("points_count", 0)
                logger.info(f"Current point count: {count}")
                return True
    except Exception:
        pass

    try:
        payload = {
            "vectors": {
                "size": EMBEDDING_DIM,
                "distance": "Cosine"
            }
        }
        req_data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{QDRANT_URL}/collections/{COLLECTION_NAME}",
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="PUT"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status not in (200, 201):
                logger.error(f"Create collection failed with status {resp.status}")
                return False
        logger.info(f"Created collection '{COLLECTION_NAME}' ({EMBEDDING_DIM}d, Cosine)")
        return True
    except Exception as e:
        logger.error(f"Failed to create collection: {e}")
        return False


def store_to_qdrant(payload: Dict[str, Any], vector: list) -> bool:
    """Store payload and vector to Qdrant."""
    try:
        point_id = generate_point_id(
            payload["content"], payload["timestamp"], payload["agent_id"]
        )

        data = {
            "points": [{
                "id": point_id,
                "vector": vector,
                "payload": payload
            }]
        }

        req_data = json.dumps(data).encode()
        req = urllib.request.Request(
            f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points",
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="PUT"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status not in (200, 201):
                logger.error(f"Qdrant store failed with status {resp.status}")
                return False
        logger.info(f"Stored [{payload['agent_id']}:{payload['role']}] → {point_id[:8]}...")
        return True
    except Exception as e:
        logger.error(f"Failed to store to Qdrant: {e}")
        return False


# Topic ID → Name mapping for The-bridge Telegram forum
TOPIC_NAME_MAP = {
    "1": "General",
    "14": "S.O.A.P Studies",
    "84": "Sundays",
    "283": "DS9 Engineering",
    "284": "Cosmic Cookies",
    "285": "Ship Alerts",
}


def extract_conversation_metadata(text: str) -> Dict[str, str]:
    """Extract Telegram topic, channel, and group info from conversation metadata in messages."""
    metadata = {}
    
    # Extract topic_id
    topic_match = re.search(r'"topic_id":\s*"(\d+)"', text)
    if topic_match:
        tid = topic_match.group(1)
        metadata["topic_id"] = tid
        # Resolve topic name from mapping
        if tid in TOPIC_NAME_MAP:
            metadata["topic_name"] = TOPIC_NAME_MAP[tid]
    
    # Extract group_subject
    group_match = re.search(r'"group_subject":\s*"([^"]*)"', text)
    if group_match:
        metadata["group_subject"] = group_match.group(1)
    
    # Extract channel (telegram, signal, etc.)
    channel_match = re.search(r'"channel":\s*"([^"]*)"', text)
    if channel_match:
        metadata["channel"] = channel_match.group(1)
    
    # Extract chat_type (group, private, etc.)
    chat_type_match = re.search(r'"chat_type":\s*"([^"]*)"', text)
    if chat_type_match:
        metadata["chat_type"] = chat_type_match.group(1)
    
    return metadata


def parse_turn(line: str) -> Optional[Dict]:
    """Parse a single line from OpenClaw session JSONL file."""
    if not line.strip():
        return None

    try:
        data = json.loads(line)

        # OpenClaw JSONL format varies — handle multiple structures
        role = data.get("role")
        content = data.get("content")
        timestamp = data.get("timestamp")

        # Some entries nest under "message"
        if not role and "message" in data:
            msg = data["message"]
            role = msg.get("role")
            content = msg.get("content")
            timestamp = msg.get("timestamp", data.get("timestamp"))

        # Skip system messages and empty content
        if not role or role == "system":
            return None

        # Extract text from content (handles string and list formats)
        text = extract_text_content(content)
        if not text or len(text.strip()) < 10:
            return None

        # Extract conversation metadata (topic, channel, etc.) from user messages
        conv_metadata = {}
        if role == "user":
            conv_metadata = extract_conversation_metadata(text)

        # Use current time if no timestamp
        if not timestamp:
            timestamp = datetime.now().isoformat()
        elif isinstance(timestamp, (int, float)):
            timestamp = datetime.fromtimestamp(timestamp / 1000).isoformat()

        result = {
            "role": role,
            "content": text,
            "timestamp": str(timestamp)
        }
        if conv_metadata:
            result["conv_metadata"] = conv_metadata

        return result
    except json.JSONDecodeError:
        return None
    except Exception as e:
        logger.error(f"Failed to parse turn: {e}")
        return None


def process_file(file_path: str, state: dict) -> int:
    """Process new lines in a session file. Returns number of turns stored."""
    agent_id = get_agent_id_from_path(file_path)
    stored = 0

    try:
        file_size = os.path.getsize(file_path)
    except OSError:
        return 0

    last_position = state.get(file_path, 0)

    if file_size <= last_position:
        return 0

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            f.seek(last_position)
            new_data = f.read()
            new_position = f.tell()

        lines = new_data.strip().split('\n')

        # Track last seen conversation metadata so assistant replies inherit it
        last_conv_meta = {}

        for line in lines:
            turn = parse_turn(line)
            if not turn:
                continue

            cleaned_content = clean_text(turn["content"])
            if not cleaned_content or len(cleaned_content) < 10:
                continue

            embedding = get_embedding(cleaned_content)
            if not embedding:
                continue

            # Update last_conv_meta from user messages, carry forward to assistant
            conv_meta = turn.get("conv_metadata", {})
            if conv_meta:
                last_conv_meta = conv_meta

            payload = {
                "agent_id": agent_id,
                "role": turn["role"],
                "content": cleaned_content[:2000],
                "timestamp": turn["timestamp"],
                "session_id": os.path.basename(file_path),
                "source": "true-recall-base"
            }

            # Add conversation metadata (topic, channel, etc.)
            active_meta = conv_meta if conv_meta else last_conv_meta
            if active_meta:
                if "topic_name" in active_meta:
                    payload["topic_name"] = active_meta["topic_name"]
                if "topic_id" in active_meta:
                    payload["topic_id"] = active_meta["topic_id"]
                if "group_subject" in active_meta:
                    payload["group_subject"] = active_meta["group_subject"]
                if "channel" in active_meta:
                    payload["channel"] = active_meta["channel"]
                if "chat_type" in active_meta:
                    payload["chat_type"] = active_meta["chat_type"]

            if store_to_qdrant(payload, embedding):
                stored += 1

        # Update position after processing all lines
        state[file_path] = new_position
        save_state(state)

    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}")

    return stored


def find_session_files(sessions_dir: Path) -> List[str]:
    """Find all JSONL session files across all agent directories."""
    files = []
    for agent_dir in sessions_dir.iterdir():
        if not agent_dir.is_dir() or agent_dir.name.startswith('.'):
            continue
        sess_dir = agent_dir / "sessions"
        if sess_dir.exists():
            for f in sess_dir.glob("*.jsonl"):
                files.append(str(f))
    return files


def poll_sessions(sessions_dir: Path, poll_interval: float = 2.0):
    """Poll-based watcher (more reliable than inotify across platforms)."""
    state = load_state()
    logger.info(f"Loaded state with {len(state)} tracked files")

    # Create collection if needed
    create_collection()

    logger.info(f"Watching sessions under: {sessions_dir}")
    logger.info(f"Qdrant: {QDRANT_URL} | Collection: {COLLECTION_NAME}")
    logger.info(f"Ollama: {OLLAMA_URL} | Model: {EMBEDDING_MODEL}")
    logger.info(f"Poll interval: {poll_interval}s")

    while True:
        try:
            files = find_session_files(sessions_dir)

            for file_path in files:
                stored = process_file(file_path, state)
                if stored > 0:
                    agent = get_agent_id_from_path(file_path)
                    logger.info(f"Processed {stored} turns from [{agent}]")

            time.sleep(poll_interval)

        except KeyboardInterrupt:
            logger.info("Stopping watcher...")
            save_state(state)
            break
        except Exception as e:
            logger.error(f"Watcher error: {e}")
            time.sleep(5)


def main():
    parser = argparse.ArgumentParser(
        description="Real-time watcher for OpenClaw sessions → Qdrant"
    )
    parser.add_argument(
        "--sessions-dir",
        default=os.path.expanduser("~/.openclaw/agents"),
        help="Path to OpenClaw agents directory"
    )
    parser.add_argument(
        "--poll-interval",
        type=float, default=2.0,
        help="Seconds between polls (default: 2.0)"
    )
    parser.add_argument(
        "--create-collection",
        action="store_true",
        help="Create Qdrant collection and exit"
    )

    args = parser.parse_args()
    sessions_dir = Path(args.sessions_dir)

    if not sessions_dir.exists():
        logger.error(f"Sessions directory not found: {sessions_dir}")
        sys.exit(1)

    if args.create_collection:
        create_collection()
        return

    poll_sessions(sessions_dir, args.poll_interval)


if __name__ == "__main__":
    main()
