#!/usr/bin/env python3

import requests
import json

# Test the store API endpoint
url = "http://localhost:8888/v1/default/banks/office/memories"

# Test data
test_data = {
    "items": [
        {
            "content": "Test memory content for debugging",
            "context": "This is a test context for the memory",
            "document_id": "test-doc-123"
        }
    ]
}

print("Testing Hindsight store API...")
print(f"URL: {url}")
print(f"Data: {json.dumps(test_data, indent=2)}")

try:
    response = requests.post(url, json=test_data, timeout=30)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")