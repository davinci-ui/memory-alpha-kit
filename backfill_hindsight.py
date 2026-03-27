#!/usr/bin/env python3
"""
Backfill key operational facts from Qdrant to Hindsight
"""

import subprocess
import json
import os
import sys

def harvest_qdrant_data():
    """Harvest data from Qdrant to understand what we have"""
    try:
        # Run the harvest script to see what data we have
        print("Harvesting Qdrant data...")
        result = subprocess.run([
            'python3', 
            '/Users/davinci/Projects/memory-alpha-kit/scripts/qdrant/harvest_sessions.py',
            '--user-id', 'davinci',
            '--dry-run'
        ], capture_output=True, text=True, timeout=30)
        
        print("Harvest output:", result.stdout)
        if result.stderr:
            print("Harvest errors:", result.stderr)
            
    except Exception as e:
        print(f"Error harvesting Qdrant data: {e}")

def test_simple_store():
    """Test simple store operation"""
    print("Testing simple store operation...")
    
    # This is a simple test to verify the API works
    test_data = {
        "items": [
            {
                "content": "Test operational fact for backfill",
                "context": "Backfill test from Qdrant data",
                "document_id": "backfill-test-123"
            }
        ]
    }
    
    print("Test data:", json.dumps(test_data, indent=2))
    
    # Try to store it directly via curl
    import requests
    
    try:
        response = requests.post(
            "http://localhost:8888/v1/default/banks/office/memories",
            json=test_data,
            timeout=5
        )
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text}")
    except requests.exceptions.Timeout:
        print("Request timed out - API is hanging")
    except Exception as e:
        print(f"Error: {e}")

def main():
    print("Starting Hindsight backfill process...")
    
    # First, let's see what data we have in Qdrant
    harvest_qdrant_data()
    
    # Then test the store operation
    test_simple_store()

if __name__ == "__main__":
    main()