#!/usr/bin/env python3
"""
Simple backfill script that works around the hanging API issue
"""

import subprocess
import json
import os
import sys
import time
import requests

def test_hindsight_health():
    """Test if Hindsight is healthy"""
    try:
        response = requests.get("http://localhost:8888/health", timeout=10)
        if response.status_code == 200:
            print("Hindsight is healthy")
            return True
        else:
            print(f"Hindsight health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"Hindsight health check error: {e}")
        return False

def get_existing_banks():
    """Get list of existing banks"""
    try:
        response = requests.get("http://localhost:8888/v1/default/banks", timeout=10)
        if response.status_code == 200:
            data = response.json()
            banks = [bank['bank_id'] for bank in data.get('banks', [])]
            print(f"Existing banks: {banks}")
            return banks
        else:
            print(f"Failed to get banks: {response.status_code}")
            return []
    except Exception as e:
        print(f"Error getting banks: {e}")
        return []

def create_simple_memory(bank_id="office", content="Test memory", context="Test context"):
    """Create a simple memory to test if API works"""
    try:
        url = f"http://localhost:8888/v1/default/banks/{bank_id}/memories"
        data = {
            "items": [{
                "content": content,
                "context": context,
                "document_id": f"test_{int(time.time())}"
            }]
        }
        
        print(f"Attempting to store memory to bank {bank_id}")
        print(f"Data: {json.dumps(data, indent=2)}")
        
        response = requests.post(url, json=data, timeout=15)
        print(f"Response status: {response.status_code}")
        print(f"Response text: {response.text[:200]}...")
        return response.status_code == 200
        
    except requests.exceptions.Timeout:
        print("Request timed out - API is hanging")
        return False
    except Exception as e:
        print(f"Error storing memory: {e}")
        return False

def backfill_from_qdrant():
    """Backfill from Qdrant using the harvest script"""
    print("Backfilling from Qdrant...")
    
    # Run the harvest script with a specific user to get some data
    try:
        result = subprocess.run([
            'python3', 
            '/Users/davinci/Projects/memory-alpha-kit/scripts/qdrant/harvest_sessions.py',
            '--user-id', 'davinci',
            '--limit', '5'  # Limit to first 5 sessions
        ], capture_output=True, text=True, timeout=60)
        
        print("Harvest output:")
        print(result.stdout[-1000:])  # Show last 1000 chars
        if result.stderr:
            print("Harvest errors:")
            print(result.stderr[-500:])  # Show last 500 chars
            
        return True
    except Exception as e:
        print(f"Error during harvest: {e}")
        return False

def main():
    print("=== Hindsight Debug and Fix ===")
    
    # Test health
    if not test_hindsight_health():
        print("Hindsight is not healthy - cannot proceed")
        return
    
    # Get banks
    banks = get_existing_banks()
    if not banks:
        print("No banks found")
        return
    
    # Test simple memory storage
    print("\\nTesting simple memory storage...")
    success = create_simple_memory()
    
    if success:
        print("✓ Simple storage works")
    else:
        print("✗ Simple storage fails - API is hanging")
    
    # Backfill from Qdrant
    print("\\nBackfilling from Qdrant...")
    backfill_from_qdrant()
    
    print("\\n=== Analysis Complete ===")
    print("The issue appears to be with the store API hanging.")
    print("We can work around this by:")
    print("1. Using the harvest script to process data")
    print("2. Creating a separate ingestion process")
    print("3. Manual backfilling of key operational facts")

if __name__ == "__main__":
    main()