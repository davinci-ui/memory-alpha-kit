#!/usr/bin/env python3
"""
Test script to verify memory bank creation functionality
"""
import requests
import time

def test_memory_banks():
    """Test creating memory banks"""
    base_url = "http://localhost:8888"
    
    # Test if Hindsight API is reachable
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        print(f"Hindsight health check: {response.status_code}")
        
        if response.status_code == 200:
            print("Hindsight API is running")
            
            # Test creating memory banks
            banks = ["office", "davinci", "hal", "sherry"]
            
            for bank_name in banks:
                bank_data = {
                    "name": bank_name,
                    "description": f"{bank_name} memory bank"
                }
                
                response = requests.post(f"{base_url}/memory_banks", 
                                       json=bank_data, 
                                       timeout=10)
                print(f"Created bank '{bank_name}': {response.status_code}")
                
                if response.status_code == 200:
                    print(f"Successfully created memory bank: {bank_name}")
                else:
                    print(f"Failed to create memory bank {bank_name}: {response.text}")
                    
        else:
            print("Hindsight API not responding correctly")
            
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Hindsight API: {e}")
        print("Hindsight may not be running or accessible")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    print("Testing Hindsight memory banks...")
    test_memory_banks()