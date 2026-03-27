#!/usr/bin/env python3
"""
Test script to verify Hindsight memory system is working
"""
import requests
import json

# Test Hindsight API
def test_hindsight():
    base_url = "http://localhost:8888"
    
    # Test if Hindsight API is reachable
    try:
        response = requests.get(f"{base_url}/health")
        print(f"Hindsight health check: {response.status_code}")
        if response.status_code == 200:
            print("Hindsight API is running")
            
            # Test creating a memory bank
            bank_data = {
                "name": "test_bank",
                "description": "Test bank for verification"
            }
            
            response = requests.post(f"{base_url}/memory_banks", 
                                   json=bank_data)
            print(f"Create bank response: {response.status_code}")
            
            # Test storing a memory
            memory_data = {
                "bank_name": "test_bank",
                "content": "This is a test memory",
                "metadata": {"source": "test"}
            }
            
            response = requests.post(f"{base_url}/memories", 
                                    json=memory_data)
            print(f"Store memory response: {response.status_code}")
            
            # Test retrieving a memory
            response = requests.get(f"{base_url}/memories?bank_name=test_bank")
            print(f"Retrieve memory response: {response.status_code}")
            
        else:
            print("Hindsight API not responding correctly")
            
    except Exception as e:
        print(f"Error testing Hindsight: {e}")

if __name__ == "__main__":
    test_hindsight()