#!/bin/bash
# Setup Qdrant collections for Memory Alpha
# Run after docker compose up -d

QDRANT_URL="${QDRANT_URL:-http://localhost:6333}"

echo "Creating conversation_logs collection..."
curl -s -X PUT "${QDRANT_URL}/collections/conversation_logs" \
  -H 'Content-Type: application/json' \
  -d '{
    "vectors": {
      "size": 1024,
      "distance": "Cosine"
    }
  }' | python3 -m json.tool

echo ""
echo "Creating memories_tr collection..."
curl -s -X PUT "${QDRANT_URL}/collections/memories_tr" \
  -H 'Content-Type: application/json' \
  -d '{
    "vectors": {
      "size": 1024,
      "distance": "Cosine"
    }
  }' | python3 -m json.tool

echo ""
echo "Pulling embedding model from Ollama..."
OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"
curl -s -X POST "${OLLAMA_URL}/api/pull" \
  -H 'Content-Type: application/json' \
  -d '{"name": "snowflake-arctic-embed2"}' | while read -r line; do echo "$line"; done

echo ""
echo "✅ Memory Alpha infrastructure ready!"
echo "   Qdrant: ${QDRANT_URL}"
echo "   Ollama: ${OLLAMA_URL}"
echo "   Model: snowflake-arctic-embed2 (1024-dim embeddings)"
