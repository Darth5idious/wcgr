# What Could Go Wrong (WCGR) - Setup Guide

## Quick Start

### 1. Install Dependencies
```bash
pip install fastapi uvicorn sse-starlette python-multipart
```

### 2. Configure Environment Variables  
The `.env` file is already configured with:
```
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key_here
```

### 3. Start the Server
```bash
./start_server.sh
```

Or manually:
```bash
export LLM_PROVIDER=groq
export GROQ_API_KEY=your_groq_api_key_here
python3 -m uvicorn api.index:app --host 127.0.0.1 --port 8000
```

### 4. Open in Browser
Navigate to: `http://127.0.0.1:8000`

## Testing

Test the API ping endpoint:
```bash
curl http://127.0.0.1:8000/api/ping
```

Expected response:
```json
{"ok":true,"hasKey":true,"model":"groq/llama-3.3-70b-versatile"}
```

Test prediction endpoint:
```bash
curl -X POST http://127.0.0.1:8000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"text":"Using production database for testing","horizon":"mid","severity":"realistic"}'
```

## Configuration

The application now uses **Groq API** instead of Gemini. The Groq implementation:
- Uses the OpenAI-compatible endpoint at `https://api.groq.com/openai/v1/chat/completions`
- Default model: `llama-3.3-70b-versatile`
- Supports streaming responses

## Troubleshooting

**Issue**: "Missing GROQ_API_KEY" error
**Solution**: Ensure environment variables are exported before starting the server

**Issue**: Server won't start  
**Solution**: Verify all dependencies are installed: `pip install -r requirements.txt`

**Issue**: CORS errors in browser
**Solution**: The server already has CORS enabled for all origins during development
