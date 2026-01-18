#!/usr/bin/env python3
"""
Test script for PII Guardrail API

Run this while the server is running:
    python test_api.py
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint."""
    print("=" * 60)
    print("Testing: GET /health")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_detect(text, expected_flagged=None):
    """Test detect endpoint."""
    print("=" * 60)
    print(f"Testing: POST /detect")
    print(f"Input: \"{text}\"")
    print("=" * 60)
    
    try:
        response = requests.post(
            f"{BASE_URL}/detect",
            json={"text": text},
            headers={"Content-Type": "application/json"}
        )
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
            
            result = data.get("result", {})
            flagged = result.get("flagged", False)
            
            if expected_flagged is not None:
                if flagged == expected_flagged:
                    print(f"\n[PASS] Expected flagged={expected_flagged}, got flagged={flagged}")
                else:
                    print(f"\n[FAIL] Expected flagged={expected_flagged}, got flagged={flagged}")
            
            return True
        else:
            print(f"Error response: {response.text}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_analyze(text):
    """Test analyze endpoint."""
    print("=" * 60)
    print(f"Testing: POST /analyze")
    print(f"Input: \"{text}\"")
    print("=" * 60)
    
    try:
        response = requests.post(
            f"{BASE_URL}/analyze",
            json={"text": text},
            headers={"Content-Type": "application/json"}
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_portkey_webhook(text):
    """Test Portkey webhook format."""
    print("=" * 60)
    print(f"Testing: POST /guardrail/pii (Portkey format)")
    print(f"Input: \"{text}\"")
    print("=" * 60)
    
    # Simulate Portkey webhook request format
    portkey_request = {
        "request": {
            "messages": [
                {"role": "user", "content": text}
            ]
        }
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/guardrail/pii",
            json=portkey_request,
            headers={
                "Content-Type": "application/json",
                "x-portkey-trace-id": "test-trace-123"
            }
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code in [200, 246]
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    print("\n" + "=" * 60)
    print("PII GUARDRAIL API TEST SUITE")
    print("=" * 60 + "\n")
    
    # Check if server is running
    print("Checking if server is running...")
    try:
        requests.get(f"{BASE_URL}/health", timeout=5)
        print("Server is running!\n")
    except:
        print("ERROR: Server is not running!")
        print("Start the server first with: python run_server.py")
        return
    
    results = []
    
    # Test 1: Health check
    results.append(("Health Check", test_health()))
    print()
    
    # Test 2: Positive cases (should flag)
    positive_tests = [
        "My Aadhaar number is 1234 5678 9012",
        "Email me at john.doe@company.com",
        "Call me at +91 98765 43210",
        "PAN: ABCDE1234F",
        "SSN: 123-45-6789",
    ]
    
    for text in positive_tests:
        results.append((f"Positive: {text[:30]}...", test_detect(text, expected_flagged=True)))
        print()
    
    # Test 3: Negative cases (should NOT flag)
    negative_tests = [
        "The meeting is scheduled for tomorrow at 10 AM",
        "Order ID: ORD-2024-789456 shipped",
        "The capital of France is Paris",
    ]
    
    for text in negative_tests:
        results.append((f"Negative: {text[:30]}...", test_detect(text, expected_flagged=False)))
        print()
    
    # Test 4: Analyze endpoint
    results.append(("Analyze endpoint", test_analyze("My email is test@example.com")))
    print()
    
    # Test 5: Portkey webhook format
    results.append(("Portkey webhook", test_portkey_webhook("My Aadhaar is 9876 5432 1098")))
    print()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {name}")
    
    print(f"\nTotal: {passed}/{total} passed")
    print("=" * 60)

if __name__ == "__main__":
    main()

