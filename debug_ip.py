
import os
import sys

# Mocking the request object to test the logic
class MockRequest:
    def __init__(self, headers, client):
        self.headers = headers
        self.client = client

class MockClient:
    def __init__(self, host):
        self.host = host

def test_ip_extraction():
    print("Testing IP Extraction Logic:\n")

    # Scenario 1: X-Forwarded-For present (Vercel/Proxy style)
    req1 = MockRequest(headers={"x-forwarded-for": "103.21.244.0, 10.0.0.1"}, client=MockClient("127.0.0.1"))
    
    forwarded_for = req1.headers.get("x-forwarded-for")
    if forwarded_for:
        ip1 = forwarded_for.split(",")[0].strip()
    else:
        ip1 = req1.client.host
    print(f"Scenario 1 (Proxy): Header='{forwarded_for}' -> Extracted='{ip1}'")

    # Scenario 2: Direct connection (Localhost)
    req2 = MockRequest(headers={}, client=MockClient("127.0.0.1"))
    
    forwarded_for = req2.headers.get("x-forwarded-for")
    if forwarded_for:
        ip2 = forwarded_for.split(",")[0].strip()
    else:
        ip2 = req2.client.host
    print(f"Scenario 2 (Direct): Header=None -> Extracted='{ip2}'")

if __name__ == "__main__":
    test_ip_extraction()
