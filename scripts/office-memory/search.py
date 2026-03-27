#!/usr/bin/env python3
"""
Office Memory — Unified search across all memory layers.

Layers:
  hindsight  — Facts, entities, patterns (Hindsight API)
  qdrant     — Conversation logs, session history (Memory Alpha)
  documents  — NAS files, PDFs, manuals (PostgreSQL + pgvector)
  workspace  — Agent memory files (MEMORY.md, memory/*.md)

Usage:
  python3 search.py --query "What do we know about ASER?"
  python3 search.py --query "training manual" --layer documents
  python3 search.py --query "March 17 decisions" --layer qdrant
  python3 search.py --retain "ASER ordered 4 containers" --bank office --context "sales"
"""

import argparse
import json
import os
import sys
import time
import subprocess

import requests
import psycopg2
from psycopg2.extras import RealDictCursor

# --- Configuration ---
HINDSIGHT_API = os.environ.get("HINDSIGHT_API", "http://localhost:8888/v1/default/banks")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "snowflake-arctic-embed2")
QDRANT_SEARCH = "/Users/davinci/Projects/memory-alpha-kit/scripts/qdrant/search_memories.py"

PG_CONFIG = {
    "host": os.environ.get("PG_HOST", "localhost"),
    "port": int(os.environ.get("PG_PORT", "5433")),
    "database": os.environ.get("PG_DB", "mirror_db"),
    "user": os.environ.get("PG_USER", "davinci"),
    "password": os.environ.get("PG_PASS", "davinci_kb_2026"),
}


def get_embedding(text: str) -> list:
    """Get embedding via Ollama API (not SentenceTransformer — uses local Ollama)."""
    resp = requests.post(
        f"{OLLAMA_URL}/api/embed",
        json={"model": EMBED_MODEL, "input": text[:8000]},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["embeddings"][0]


def classify_query(query: str) -> list:
    """
    Classify query and return priority-ordered layers to search.
    Uses keyword/pattern matching (no LLM calls).
    
    Order matters: check most specific patterns first, then fall through
    to broader matches. Every path returns at least 2 layers for coverage.
    """
    q = query.lower()

    # 1. Documents — file/manual/SOP lookups
    if any(kw in q for kw in [
        "document", "manual", "file", "pdf", "checklist", "sop",
        "find the file", "find the doc", "template", "form",
    ]):
        return ["documents", "workspace"]

    # 2. Workspace — preferences, rules, identity, config, how-we-work
    if any(kw in q for kw in [
        "preference", "rule", "identity", "tone", "how do we",
        "our approach", "our style", "our brand", "non-negotiable",
        "principle", "guideline", "standard", "policy",
    ]):
        return ["workspace", "hindsight"]

    # 3. Conversation recall — past decisions, discussions
    if any(kw in q for kw in [
        "when did we", "decided", "conversation", "discussed",
        "last time", "remember when", "talked about", "agreed",
        "meeting", "we said", "told me", "mentioned",
    ]):
        return ["qdrant", "hindsight"]

    # 4. Entity/people/fact lookup
    if any(kw in q for kw in [
        "who is", "who are", "what is", "what are",
        "tell me about", "about ", "entity",
    ]):
        return ["hindsight", "qdrant"]

    # 5. Default — search everything
    return ["hindsight", "qdrant", "documents", "workspace"]


# --- Hindsight ---
def search_hindsight(query: str, bank_id: str) -> list:
    """Recall from Hindsight memory bank."""
    try:
        resp = requests.post(
            f"{HINDSIGHT_API}/{bank_id}/memories/recall",
            json={"query": query},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("results", []):
            results.append({
                "layer": "hindsight",
                "bank": bank_id,
                "type": item.get("type", "unknown"),
                "text": item.get("text", ""),
                "entities": item.get("entities", []),
                "context": item.get("context"),
            })
        return results
    except Exception as e:
        return [{"layer": "hindsight", "error": str(e)}]


def retain_hindsight(content: str, bank_id: str, context: str) -> dict:
    """Store a memory into Hindsight."""
    try:
        resp = requests.post(
            f"{HINDSIGHT_API}/{bank_id}/memories",
            json={
                "items": [{
                    "content": content,
                    "context": context,
                    "document_id": f"stored_{int(time.time())}",
                }]
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


# --- Qdrant (Memory Alpha) ---
def search_qdrant(query: str) -> list:
    """Search conversation logs via Memory Alpha search script."""
    try:
        result = subprocess.run(
            ["python3", QDRANT_SEARCH, query],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            # Script might print results to stdout even on non-zero exit
            pass
        output = result.stdout.strip()
        if not output:
            return []
        # The search script may output plain text or JSON — handle both
        try:
            data = json.loads(output)
            if isinstance(data, list):
                return [{"layer": "qdrant", **item} for item in data]
            return [{"layer": "qdrant", "data": data}]
        except json.JSONDecodeError:
            # Plain text output — return as single result
            return [{"layer": "qdrant", "text": output}]
    except Exception as e:
        return [{"layer": "qdrant", "error": str(e)}]


# --- Document KB (PostgreSQL + pgvector) ---
def search_documents(query: str) -> list:
    """Hybrid search: vector similarity + full-text search."""
    results = []
    try:
        conn = psycopg2.connect(**PG_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Vector search
        try:
            emb = get_embedding(query)
            cur.execute(
                """
                SELECT source_path,
                       LEFT(content, 500) as excerpt,
                       1 - (embedding <=> %s::vector) as similarity
                FROM documents
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector
                LIMIT 5
                """,
                (str(emb), str(emb)),
            )
            for row in cur.fetchall():
                results.append({
                    "layer": "documents",
                    "method": "vector",
                    "path": row["source_path"],
                    "excerpt": row["excerpt"],
                    "similarity": round(float(row["similarity"]), 4),
                })
        except Exception as e:
            results.append({"layer": "documents", "method": "vector", "error": str(e)})

        # Full-text search
        try:
            cur.execute(
                """
                SELECT source_path, LEFT(content, 500) as excerpt
                FROM documents
                WHERE content_tsv @@ plainto_tsquery(%s)
                LIMIT 5
                """,
                (query,),
            )
            for row in cur.fetchall():
                results.append({
                    "layer": "documents",
                    "method": "fulltext",
                    "path": row["source_path"],
                    "excerpt": row["excerpt"],
                })
        except Exception as e:
            results.append({"layer": "documents", "method": "fulltext", "error": str(e)})

        cur.close()
        conn.close()
    except Exception as e:
        results.append({"layer": "documents", "error": str(e)})

    return results


def search_workspace(query: str, workspace_dir: str = None) -> list:
    """Search OpenClaw's workspace memory files."""
    results = []
    if workspace_dir is None:
        workspace_dir = os.environ.get("OPENCLAW_WORKSPACE", "/Users/davinci/.openclaw/workspace")
    
    # Check if workspace directory exists
    if not os.path.exists(workspace_dir):
        return results
    
    # Read MEMORY.md
    memory_md_path = os.path.join(workspace_dir, "MEMORY.md")
    if os.path.exists(memory_md_path):
        try:
            with open(memory_md_path, "r", encoding="utf-8") as f:
                content = f.read()
                if query.lower() in content.lower():
                    # Split by headers and find relevant sections
                    sections = content.split("## ")
                    for section in sections:
                        if section.strip() and query.lower() in section.lower():
                            # Return first 500 chars of the section
                            section_content = section[:500]
                            results.append({
                                "layer": "workspace",
                                "source": "MEMORY.md",
                                "text": section_content,
                                "match_type": "keyword"
                            })
        except Exception:
            pass  # Ignore errors reading the file
    
    # Read all memory/*.md files
    memory_dir = os.path.join(workspace_dir, "memory")
    if os.path.exists(memory_dir):
        try:
            for filename in os.listdir(memory_dir):
                if filename.endswith(".md"):
                    file_path = os.path.join(memory_dir, filename)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            if query.lower() in content.lower():
                                # Split by headers and find relevant sections
                                sections = content.split("## ")
                                for section in sections:
                                    if section.strip() and query.lower() in section.lower():
                                        # Return first 500 chars of the section
                                        section_content = section[:500]
                                        results.append({
                                            "layer": "workspace",
                                            "source": filename,
                                            "text": section_content,
                                            "match_type": "keyword"
                                        })
                    except Exception:
                        continue  # Skip files that can't be read
        except Exception:
            pass  # Ignore errors reading the directory
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Office Memory — Unified search")
    parser.add_argument("--query", help="Search query")
    parser.add_argument(
        "--layer",
        choices=["auto", "hindsight", "qdrant", "documents", "workspace", "all"],
        default="auto",
        help="Memory layer to search (default: auto)",
    )
    parser.add_argument("--bank", default="office", help="Hindsight bank (default: office)")
    parser.add_argument("--retain", help="Content to store in Hindsight")
    parser.add_argument("--context", help="Context for --retain")
    parser.add_argument("--limit", type=int, default=5, help="Max results per layer")
    parser.add_argument("--verbose", action="store_true", help="Show routing information")
    parser.add_argument("--workspace", help="Workspace dir for workspace layer (default: $OPENCLAW_WORKSPACE or DaVinci's)")
    args = parser.parse_args()

    # Retain mode
    if args.retain:
        if not args.context:
            print(json.dumps({"error": "--context required when using --retain"}))
            sys.exit(1)
        result = retain_hindsight(args.retain, args.bank, args.context)
        print(json.dumps(result, indent=2))
        return

    # Search mode
    if not args.query:
        parser.print_help()
        sys.exit(1)

    results = []
    routing_info = None
    
    # Determine layers to search
    if args.layer == "auto":
        # Use smart query router
        layers_to_search = classify_query(args.query)
        if args.verbose:
            routing_info = {
                "classified_as": " ".join(classify_query(args.query)),
                "layers_searched": layers_to_search,
                "total_results": 0
            }
        
        # Search top 2 layers first, then fallback to remaining layers if needed
        searched_layers = []
        for layer in layers_to_search[:2]:
            if layer == "hindsight":
                results.extend(search_hindsight(args.query, args.bank))
                searched_layers.append("hindsight")
            elif layer == "qdrant":
                results.extend(search_qdrant(args.query))
                searched_layers.append("qdrant")
            elif layer == "documents":
                results.extend(search_documents(args.query))
                searched_layers.append("documents")
            elif layer == "workspace":
                results.extend(search_workspace(args.query, args.workspace))
                searched_layers.append("workspace")
        
        # If combined results < 2, search remaining layers
        if len(results) < 2 and len(layers_to_search) > 2:
            for layer in layers_to_search[2:]:
                if layer not in searched_layers:
                    if layer == "hindsight":
                        results.extend(search_hindsight(args.query, args.bank))
                    elif layer == "qdrant":
                        results.extend(search_qdrant(args.query))
                    elif layer == "documents":
                        results.extend(search_documents(args.query))
                    elif layer == "workspace":
                        results.extend(search_workspace(args.query, args.workspace))
    else:
        # Explicit layer search
        if args.layer in ("all", "hindsight"):
            results.extend(search_hindsight(args.query, args.bank))
        if args.layer in ("all", "qdrant"):
            results.extend(search_qdrant(args.query))
        if args.layer in ("all", "documents"):
            results.extend(search_documents(args.query))
        if args.layer in ("all", "workspace"):
            results.extend(search_workspace(args.query, args.workspace))

    # Sort results by relevance
    priority_layers = classify_query(args.query) if args.layer == "auto" else []

    def score_result(result):
        score = 0
        layer = result.get("layer")
        if result.get("entities"):
            score += 2  # Hindsight with entities
        if layer == "qdrant":
            score += 1
        if layer == "documents" and result.get("similarity", 0) > 0.4:
            score += 1
        if layer == "workspace":
            score += 1
        # Layer priority bonus from router
        if priority_layers:
            if layer == priority_layers[0]:
                score += 3
            elif len(priority_layers) > 1 and layer == priority_layers[1]:
                score += 1
        # Penalize error results
        if "error" in result:
            score -= 10
        return score

    results = sorted(results, key=score_result, reverse=True)

    # Add routing info if verbose
    if args.verbose and routing_info:
        routing_info["total_results"] = len(results)
        output = {"results": results, "_routing": routing_info}
    else:
        output = {"results": results}
    
    print(json.dumps(output, indent=2, default=str))


if __name__ == "__main__":
    main()
