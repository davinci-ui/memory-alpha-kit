#!/usr/bin/env python3
"""
Ingest Mac session transcripts (OpenClaw v3 JSONL format) into Qdrant.
Extracts user/assistant message pairs and stores with embeddings.
"""

import hashlib
import json
import os
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = os.environ.get("QDRANT_COLLECTION", "conversation_logs")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = "snowflake-arctic-embed2"
SESSIONS_DIR = Path(os.environ.get("SESSIONS_DIR", os.path.expanduser("~/.openclaw/sessions")))
BATCH_SIZE = 10
SOURCE_TAG = "mac-rin-session"

def get_embedding(text: str) -> Optional[List[float]]:
    """Get embedding from Ollama."""
    try:
        payload = json.dumps({"model": EMBED_MODEL, "input": text}).encode()
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/embed",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            embeddings = data.get("embeddings", [])
            if embeddings:
                return embeddings[0]
    except Exception as e:
        print(f"  [Embed] Error: {e}", file=sys.stderr)
    return None

def content_hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()

def check_duplicate(hash_val: str) -> bool:
    """Check if content hash already exists in Qdrant."""
    try:
        payload = json.dumps({
            "filter": {"must": [{"key": "content_hash", "match": {"value": hash_val}}]},
            "limit": 1
        }).encode()
        req = urllib.request.Request(
            f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points/scroll",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            points = data.get("result", {}).get("points", [])
            return len(points) > 0
    except:
        return False

def store_point(point_id: str, vector: List[float], payload: Dict) -> bool:
    """Store a single point in Qdrant."""
    try:
        data = json.dumps({
            "points": [{
                "id": point_id,
                "vector": vector,
                "payload": payload
            }]
        }).encode()
        req = urllib.request.Request(
            f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points",
            data=data,
            headers={"Content-Type": "application/json"},
            method="PUT"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return result.get("status") == "ok"
    except Exception as e:
        print(f"  [Store] Error: {e}", file=sys.stderr)
        return False

def extract_text_content(content) -> str:
    """Extract text from message content (handles string or list format)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)
    return str(content)

def parse_v3_session(filepath: Path) -> List[Dict]:
    """Parse OpenClaw v3 session JSONL into conversation turns."""
    turns = []
    messages = []
    session_id = filepath.stem
    session_ts = None

    try:
        with open(filepath, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                except:
                    continue

                entry_type = entry.get("type", "")

                if entry_type == "session":
                    session_ts = entry.get("timestamp", "")
                    continue

                if entry_type == "message":
                    msg = entry.get("message", {})
                    role = msg.get("role", "")
                    content = extract_text_content(msg.get("content", ""))
                    ts = entry.get("timestamp", session_ts or "")

                    if role in ("user", "assistant") and content.strip():
                        messages.append({
                            "role": role,
                            "content": content.strip(),
                            "timestamp": ts
                        })

        # Pair user/assistant turns
        i = 0
        while i < len(messages):
            if messages[i]["role"] == "user":
                user_msg = messages[i]["content"]
                ai_msg = ""
                ts = messages[i]["timestamp"]

                if i + 1 < len(messages) and messages[i + 1]["role"] == "assistant":
                    ai_msg = messages[i + 1]["content"]
                    i += 2
                else:
                    i += 1

                # Skip very short or system-like messages
                if len(user_msg) < 10 and not ai_msg:
                    continue

                combined = f"User: {user_msg}\n\nAssistant: {ai_msg}" if ai_msg else f"User: {user_msg}"

                # Truncate very long entries for embedding
                if len(combined) > 4000:
                    combined = combined[:4000] + "..."

                turns.append({
                    "text": combined,
                    "user_msg": user_msg[:500],
                    "ai_msg": ai_msg[:500],
                    "timestamp": ts,
                    "session_id": session_id,
                    "source": SOURCE_TAG
                })
            else:
                i += 1

    except Exception as e:
        print(f"[Parse] Error parsing {filepath.name}: {e}", file=sys.stderr)

    return turns

def main():
    print(f"[Ingest] Mac Session Ingestion — {datetime.now().isoformat()}")
    print(f"[Ingest] Source: {SESSIONS_DIR}")
    print(f"[Ingest] Target: {QDRANT_URL}/collections/{COLLECTION_NAME}")
    print()

    session_files = sorted(
        [f for f in SESSIONS_DIR.glob("*.jsonl") if not f.name.startswith("._")],
        key=lambda p: p.stat().st_mtime
    )

    print(f"[Ingest] Found {len(session_files)} session files")

    total_stored = 0
    total_skipped = 0
    total_errors = 0

    for idx, session_file in enumerate(session_files, 1):
        print(f"\n[{idx}/{len(session_files)}] Processing {session_file.name} ({session_file.stat().st_size/1024:.0f}KB)")

        turns = parse_v3_session(session_file)
        print(f"  Extracted {len(turns)} conversation turns")

        for turn_idx, turn in enumerate(turns):
            hash_val = content_hash(turn["text"])

            if check_duplicate(hash_val):
                total_skipped += 1
                continue

            # Get embedding
            embedding = get_embedding(turn["text"])
            if not embedding:
                total_errors += 1
                continue

            # Generate UUID from hash
            point_id = str(hashlib.md5(f"{turn['session_id']}:{hash_val}".encode()).hexdigest())

            payload = {
                "text": turn["text"],
                "user_msg": turn["user_msg"],
                "ai_msg": turn["ai_msg"],
                "timestamp": turn["timestamp"],
                "session_id": turn["session_id"],
                "source": turn["source"],
                "content_hash": hash_val,
                "user_id": os.environ.get("MEMORY_USER_ID", "default"),
                "agent_id": "rin",
                "ingested_at": datetime.now().isoformat()
            }

            if store_point(point_id, embedding, payload):
                total_stored += 1
            else:
                total_errors += 1

            # Progress update every 10 turns
            if (turn_idx + 1) % 10 == 0:
                print(f"  ... {turn_idx + 1}/{len(turns)} turns processed")

            # Small delay to not overwhelm Ollama on CPU
            time.sleep(0.1)

    print(f"\n[Ingest] === COMPLETE ===")
    print(f"[Ingest] Stored: {total_stored}")
    print(f"[Ingest] Skipped (duplicates): {total_skipped}")
    print(f"[Ingest] Errors: {total_errors}")

    # Verify final count
    try:
        req = urllib.request.Request(f"{QDRANT_URL}/collections/{COLLECTION_NAME}")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
            count = data.get("result", {}).get("points_count", "?")
            print(f"[Ingest] Qdrant total points now: {count}")
    except:
        pass

if __name__ == "__main__":
    main()
