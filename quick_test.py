#!/usr/bin/env python3
import json
import urllib.request
import sys

import os

# Quick Groq API test
api_key = os.environ.get("GROQ_API_KEY", "").strip()
req_body = {
    "model": "llama-3.3-70b-versatile",
    "messages": [{"role": "user", "content": "Say hello"}],
    "max_tokens": 50,
}
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}",
}

try:
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(req_body).encode(),
        headers=headers,
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read())
        print("SUCCESS:", data["choices"][0]["message"]["content"])
        sys.exit(0)
except Exception as e:
    print("FAILED:", str(e))
    sys.exit(1)
