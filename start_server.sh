#!/bin/bash
# WCGR Server Startup Script

# Load environment variables from .env file
if [ -f .env ]; then
    export $(cat .env | xargs)
fi

# Verify Groq configuration
echo "=== WCGR Server Configuration ==="
echo "LLM Provider: ${LLM_PROVIDER:-NOT SET}"
echo "Groq API Key: ${GROQ_API_KEY:0:15}... (${#GROQ_API_KEY} chars)"
echo "================================="

# Start the server
python3 -m uvicorn api.index:app --host 127.0.0.1 --port 8000 --reload
