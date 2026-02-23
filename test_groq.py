#!/usr/bin/env python3
import json
import os
import urllib.request

# Test Groq API connectivity
api_key = os.environ.get("GROQ_API_KEY", "").strip()
print(f"API Key present: {bool(api_key)}")
print(f"API Key (first 10 chars): {api_key[:10]}..." if api_key else "NO KEY")

if not api_key:
    print("ERROR: GROQ_API_KEY not found in environment")
    exit(1)

model = "llama-3.3-70b-versatile"
endpoint = "https://api.groq.com/openai/v1/chat/completions"

req_body = {
    "model": model,
    "messages": [{"role": "user", "content": "Say 'Hello from Groq!' and nothing else."}],
    "temperature": 0.7,
    "max_tokens": 50,
    "stream": False,
}

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}",
    "User-Agent": "WCGR-Test/1.0",
}

req = urllib.request.Request(
    url=endpoint, 
    data=json.dumps(req_body).encode("utf-8"), 
    headers=headers, 
    method="POST"
)

try:
    print(f"\nTesting Groq API with model: {model}")
    print(f"Endpoint: {endpoint}\n")
    
    with urllib.request.urlopen(req, timeout=30) as resp:
        response_data = json.loads(resp.read().decode("utf-8"))
        content = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
        print(f"✓ SUCCESS! Response from Groq:")
        print(f"  {content}\n")
        print(f"Full response structure:")
        print(json.dumps(response_data, indent=2))
        
except urllib.error.HTTPError as e:
    print(f"✗ HTTP Error {e.code}: {e.reason}")
    try:
        error_body = e.read().decode("utf-8")
        print(f"Error details: {error_body}")
    except:
        pass
except Exception as e:
    print(f"✗ Error: {type(e).__name__}: {str(e)}")
