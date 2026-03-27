#!/usr/bin/env python3
"""
Fix for Hindsight ingestion pipeline and memory storage issues
"""

import subprocess
import json
import os
import sys
import time
from pathlib import Path

def create_ingestion_script():
    """Create a proper ingestion script that can backfill from Qdrant to Hindsight"""
    
    script_content = '''
#!/usr/bin/env python3
"""
Ingestion script to backfill operational facts from Qdrant to Hindsight
"""

import subprocess
import json
import os
import sys
import time
import requests
from datetime import datetime

# Configuration
HINDSIGHT_API = "http://localhost:8888/v1/default/banks"
QDRANT_SEARCH_SCRIPT = "/Users/davinci/Projects/memory-alpha-kit/scripts/qdrant/search_memories.py"

def search_qdrant(query):
    """Search Qdrant for operational facts"""
    try:
        result = subprocess.run(
            ["python3", QDRANT_SEARCH_SCRIPT, query],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception as e:
        print(f"Error searching Qdrant: {e}")
        return None

def store_to_hindsight(content, bank_id="office", context="backfilled operational fact"):
    """Store content to Hindsight memory bank"""
    try:
        url = f"{HINDSIGHT_API}/{bank_id}/memories"
        data = {
            "items": [{
                "content": content,
                "context": context,
                "document_id": f"backfill_{int(time.time())}_{bank_id}"
            }]
        }
        
        response = requests.post(url, json=data, timeout=30)
        if response.status_code == 200:
            print(f"Successfully stored to {bank_id}: {content[:100]}...")
            return True
        else:
            print(f"Failed to store to {bank_id}: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Error storing to Hindsight: {e}")
        return False

def backfill_operational_facts():
    """Backfill key operational facts from Qdrant to Hindsight"""
    
    # Key operational queries to search for
    queries = [
        "operational procedure",
        "training manual",
        "system configuration",
        "process workflow",
        "important decision",
        "critical task",
        "key fact",
        "important information"
    ]
    
    print("Starting backfill of operational facts...")
    
    for i, query in enumerate(queries):
        print(f"\\n[{i+1}/{len(queries)}] Searching for: {query}")
        
        # Search Qdrant for this query
        result = search_qdrant(query)
        if result:
            print(f"Found result: {result[:200]}...")
            # Store this as a memory in Hindsight
            store_to_hindsight(
                content=result,
                context=f"Backfilled operational fact: {query}",
                bank_id="office"
            )
        else:
            print("No results found")
        
        # Be nice to the system
        time.sleep(1)
    
    print("\\nBackfill process completed!")

if __name__ == "__main__":
    backfill_operational_facts()
'''
    
    with open('/Users/davinci/Projects/memory-alpha-kit/scripts/hindsight/ingestion_backfill.py', 'w') as f:
        f.write(script_content)
    
    # Make it executable
    os.chmod('/Users/davinci/Projects/memory-alpha-kit/scripts/hindsight/ingestion_backfill.py', 0o755)
    
    print("Created ingestion_backfill.py script")

def main():
    print("Fixing Hindsight ingestion pipeline...")
    
    # Create the ingestion script
    create_ingestion_script()
    
    print("Ingestion pipeline fix created successfully!")
    print("Run with: python3 /Users/davinci/Projects/memory-alpha-kit/scripts/hindsight/ingestion_backfill.py")

if __name__ == "__main__":
    main()