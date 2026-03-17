#!/usr/bin/env python3
"""
Memory Alpha Search - Semantic search for the Memory Alpha knowledge base

Queries the memory_alpha Qdrant collection with semantic search.
"""

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime
from typing import List, Dict, Optional

# Configuration
QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = "memory_alpha"
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434") + "/v1"

def get_embedding(text: str) -> Optional[List[float]]:
    """Generate embedding using snowflake-arctic-embed2"""
    data = json.dumps({
        "model": "snowflake-arctic-embed2",
        "input": text[:8192]
    }).encode()
    
    req = urllib.request.Request(
        f"{OLLAMA_URL}/embeddings",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode())
            return result["data"][0]["embedding"]
    except Exception as e:
        print(f"Embedding error: {e}", file=sys.stderr)
        return None

def search_qdrant(query: str, limit: int = 5) -> List[Dict]:
    """Search Qdrant for relevant documents"""
    # Generate query embedding
    query_embedding = get_embedding(query)
    if not query_embedding:
        print("Failed to generate query embedding", file=sys.stderr)
        return []
    
    # Prepare search payload
    search_payload = {
        "vector": query_embedding,
        "limit": limit,
        "with_payload": True
    }
    
    # Perform search
    req = urllib.request.Request(
        f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points/search",
        data=json.dumps(search_payload).encode(),
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode())
            
            # Process results
            hits = []
            for hit in result.get("result", []):
                payload = hit.get("payload", {})
                hits.append({
                    "file_path": payload.get("file_path", "Unknown"),
                    "chunk_text": payload.get("chunk_text", "").strip(),
                    "similarity_score": hit.get("score", 0.0),
                    "last_modified": payload.get("last_modified", "Unknown"),
                    "chunk_index": payload.get("chunk_index", 0),
                    "file_size": payload.get("file_size", 0)
                })
            
            return hits
    except Exception as e:
        print(f"Search error: {e}", file=sys.stderr)
        return []

def format_results(results: List[Dict]) -> str:
    """Format search results for display"""
    if not results:
        return "No relevant results found."
    
    output = []
    output.append(f"Found {len(results)} relevant results:")
    output.append("")
    
    for i, result in enumerate(results, 1):
        output.append(f"{i}. File: {result['file_path']}")
        output.append(f"   Similarity: {result['similarity_score']:.4f}")
        output.append(f"   Modified: {result['last_modified']}")
        output.append(f"   Chunk: {result['chunk_index']}")
        output.append(f"   Content: {result['chunk_text'][:300]}{'...' if len(result['chunk_text']) > 300 else ''}")
        output.append("")
    
    return "\n".join(output)

def main():
    parser = argparse.ArgumentParser(description="Search Memory Alpha knowledge base")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--limit", type=int, default=5, help="Number of results to return (default: 5)")
    parser.add_argument("--context", help="Additional context for the search")
    args = parser.parse_args()
    
    # Combine query with context if provided
    full_query = args.query
    if args.context:
        full_query = f"{args.query} - {args.context}"
    
    print(f"Searching Memory Alpha for: '{full_query}'")
    print(f"Limit: {args.limit} results")
    print("-" * 50)
    
    # Perform search
    results = search_qdrant(full_query, args.limit)
    
    # Format and display results
    formatted_results = format_results(results)
    print(formatted_results)
    
    # Also return JSON for programmatic use
    print("\nJSON Results:")
    print(json.dumps(results, indent=2, default=str))

if __name__ == "__main__":
    main()