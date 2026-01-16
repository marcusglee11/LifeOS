#!/usr/bin/env python3
"""Debug script to examine OpenCode API response format."""
import requests
import json

BASE_URL = "http://127.0.0.1:4096"

print("1. Creating session...")
resp = requests.post(f"{BASE_URL}/session", json={"title": "Debug"}, timeout=30)
print(f"   Status: {resp.status_code}")
session_id = resp.json()["id"]
print(f"   Session ID: {session_id}")

print("\n2. Sending message...")
resp2 = requests.post(
    f"{BASE_URL}/session/{session_id}/message",
    json={"parts": [{"type": "text", "text": "Reply with exactly: {\"msg\": \"hello\"}"}]},
    timeout=60
)
print(f"   Status: {resp2.status_code}")
print(f"   Content-Type: {resp2.headers.get('Content-Type')}")
print(f"   Response type: {type(resp2.text)}")
print(f"\n3. Response text (first 3000 chars):")
print(resp2.text[:3000])

print("\n4. Trying to parse as JSON...")
try:
    data = resp2.json()
    print(f"   Parsed as JSON: {type(data)}")
    print(f"   Keys: {data.keys() if isinstance(data, dict) else 'N/A'}")
    print(f"   Data: {json.dumps(data, indent=2)[:1000]}")
except Exception as e:
    print(f"   Failed to parse JSON: {e}")
