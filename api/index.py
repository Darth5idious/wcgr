import json
import os
import time
import urllib.request
import urllib.parse
import urllib.error
from typing import AsyncGenerator
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

app = FastAPI()

# Database connection utility
@contextmanager
def get_db_connection():
    conn = None
    try:
        database_url = get_env_var("POSTGRES_URL")
        if database_url:
            conn = psycopg2.connect(database_url)
            yield conn
        else:
            yield None
    except Exception as e:
        print(f"Database connection error: {e}")
        yield None
    finally:
        if conn:
            conn.close()

# Initialize database table on startup
@app.on_event("startup")
async def startup():
    with get_db_connection() as conn:
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS queries (
                        id SERIAL PRIMARY KEY,
                        user_text TEXT NOT NULL,
                        horizon VARCHAR(50),
                        severity VARCHAR(50),
                        model_used VARCHAR(100),
                        response_preview TEXT,
                        ip_address VARCHAR(45),
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    );
                    -- Add ip_address column if it doesn't exist (for existing tables)
                    DO $$
                    BEGIN
                        IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='queries' AND column_name='ip_address') THEN
                            ALTER TABLE queries ADD COLUMN ip_address VARCHAR(45);
                        END IF;
                    END
                    $$;
                """)
                conn.commit()
                cursor.close()
                print("Database table initialized successfully")
            except Exception as e:
                print(f"Database initialization error: {e}")

# serve index.html if possible
@app.get("/")
async def root():
    try:
        # Try to read index.html from the root directory
        # In Vercel serverless, the root of the project is often the cwd or /var/task
        path = os.path.join(os.getcwd(), "index.html")
        if not os.path.exists(path):
            # Try one level up if we are in /api
            path = os.path.join(os.getcwd(), "..", "index.html")
        
        if os.path.exists(path):
            with open(path, "r") as f:
                return HTMLResponse(content=f.read())
        return HTMLResponse(content="<h1>WCGR API Active</h1><p>Frontend file not found. Check deployment structure.</p>")
    except Exception as e:
        return HTMLResponse(content=f"<h1>Error</h1><p>{str(e)}</p>")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_env_var(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()

async def _gemini_stream(prompt: str, config: dict) -> AsyncGenerator[str, None]:
    api_key = get_env_var("GEMINI_API_KEY")
    if not api_key:
        yield f"data: {json.dumps({'error': 'Missing GEMINI_API_KEY'})}\n\n"
        return

    model = get_env_var("GEMINI_MODEL", "gemini-2.0-flash")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{urllib.parse.quote(model)}:streamGenerateContent?alt=sse&key={urllib.parse.quote(api_key)}"
    )

    req_body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": config.get("temperature", 0.7),
            "maxOutputTokens": 800,
        },
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(req_body).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "WCGR-Vercel/1.0"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            for line in resp:
                line = line.decode("utf-8").strip()
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                    text = "".join(p.get("text", "") for p in parts if "text" in p)
                    if text:
                        yield f"data: {json.dumps({'output': text})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"

async def _openai_stream(prompt: str, config: dict) -> AsyncGenerator[str, None]:
    api_key = get_env_var("OPENAI_API_KEY")
    base_url = get_env_var("OPENAI_BASE_URL")
    if not api_key and not base_url:
        yield f"data: {json.dumps({'error': 'Missing API Credentials'})}\n\n"
        return

    model = get_env_var("OPENAI_MODEL", "llama-3.3-70b-versatile")
    endpoint = (base_url.rstrip("/") + "/chat/completions") if base_url else "https://api.openai.com/v1/chat/completions"

    req_body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": config.get("temperature", 0.7),
        "max_tokens": 800,
        "stream": True,
    }

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "WCGR-Vercel/1.0",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(url=endpoint, data=json.dumps(req_body).encode("utf-8"), headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            for line in resp:
                line = line.decode("utf-8").strip()
                if line.startswith("data: "):
                    if line == "data: [DONE]":
                        break
                    data = json.loads(line[6:])
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    if "content" in delta:
                        yield f"data: {json.dumps({'output': delta['content']})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"

async def _anthropic_stream(prompt: str, config: dict) -> AsyncGenerator[str, None]:
    api_key = get_env_var("ANTHROPIC_API_KEY")
    if not api_key:
        yield f"data: {json.dumps({'error': 'Missing ANTHROPIC_API_KEY'})}\n\n"
        return

    model = get_env_var("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620")

    req_body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 800,
        "temperature": config.get("temperature", 0.7),
        "stream": True,
    }

    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "User-Agent": "WCGR-Vercel/1.0",
    }

    req = urllib.request.Request(
        url="https://api.anthropic.com/v1/messages", data=json.dumps(req_body).encode("utf-8"), headers=headers, method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            for line in resp:
                line = line.decode("utf-8").strip()
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    if data.get("type") == "content_block_delta":
                        text = data.get("delta", {}).get("text", "")
                        yield f"data: {json.dumps({'output': text})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"

async def _groq_stream(prompt: str, config: dict) -> AsyncGenerator[str, None]:
    api_key = get_env_var("GROQ_API_KEY")
    if not api_key:
        yield f"data: {json.dumps({'error': 'Missing GROQ_API_KEY'})}\n\n"
        return

    model = get_env_var("GROQ_MODEL", "llama-3.3-70b-versatile")
    endpoint = "https://api.groq.com/openai/v1/chat/completions"

    req_body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": config.get("temperature", 0.7),
        "max_tokens": 800,
        "stream": True,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "WCGR-Vercel/1.0",
    }

    req = urllib.request.Request(url=endpoint, data=json.dumps(req_body).encode("utf-8"), headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            for line in resp:
                line = line.decode("utf-8").strip()
                if line.startswith("data: "):
                    if line == "data: [DONE]":
                        break
                    data = json.loads(line[6:])
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    if "content" in delta:
                        yield f"data: {json.dumps({'output': delta['content']})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"

@app.get("/api/ping")
async def ping():
    provider = get_env_var("LLM_PROVIDER", "gemini").lower()
    model = "unknown"
    has_key = False

    if provider == "gemini":
        model = get_env_var("GEMINI_MODEL", "gemini-2.0-flash")
        has_key = bool(get_env_var("GEMINI_API_KEY"))
    elif provider == "openai":
        model = get_env_var("OPENAI_MODEL", "llama-3.3-70b-versatile")
        has_key = bool(get_env_var("OPENAI_API_KEY")) or bool(get_env_var("OPENAI_BASE_URL"))
    elif provider == "anthropic":
        model = get_env_var("ANTHROPIC_MODEL", "claude-3-5-sonnet")
        has_key = bool(get_env_var("ANTHROPIC_API_KEY"))
    elif provider == "groq":
        model = get_env_var("GROQ_MODEL", "llama-3.3-70b-versatile")
        has_key = bool(get_env_var("GROQ_API_KEY"))

    return {"ok": True, "hasKey": has_key, "model": f"{provider}/{model}"}

@app.post("/api/predict")
async def predict(request: Request):
    try:
        body = await request.json()
    except:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})
        
    text = (body.get("text") or "").strip()
    horizon = (body.get("horizon") or "mid").strip()
    severity = (body.get("severity") or "realistic").strip()

    if not text:
        return JSONResponse(status_code=400, content={"error": "Missing 'text'"})

    provider = get_env_var("LLM_PROVIDER", "gemini").lower()
    
    horizon_map = {
        "near": "near-term (hours to days)",
        "mid": "mid-term (weeks to months)",
        "far": "far-term (years)",
    }
    horizon_desc = horizon_map.get(horizon, horizon_map["mid"])
    tone = "realistic and plausible" if severity == "realistic" else "aggressive worst-case but still plausible"

    prompt = f"""You are an adversarial-but-helpful risk forecaster.
Task: Given the user's input, describe the WORST PLAUSIBLE chain of events it could cause.

Rules:
- Be specific and concrete: actors, incentives, failure modes, second-order effects.
- Keep it plausible (no sci-fi).
- Time horizon: {horizon_desc}.
- Tone: {tone}.
- Output format:
  1) One-sentence headline.
  2) Bullet timeline (5-10 bullets) of escalation.
  3) Top 5 failure points (each with: why it happens + how to mitigate).
  4) A short "If you do nothing" ending.

User input:
{text}
"""
    config = {"temperature": 0.9 if severity != "realistic" else 0.7}

    async def stream_logic():
        try:
            if provider == "openai":
                async for chunk in _openai_stream(prompt, config):
                    yield chunk
            elif provider == "anthropic":
                async for chunk in _anthropic_stream(prompt, config):
                    yield chunk
            elif provider == "groq":
                async for chunk in _groq_stream(prompt, config):
                    yield chunk
            else:
                async for chunk in _gemini_stream(prompt, config):
                    yield chunk
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(stream_logic(), media_type="text/event-stream")

# Log query in background (called after predict)
@app.post("/api/log_query")
async def log_query(request: Request):
    try:
        body = await request.json()
        text = body.get("text", "")
        horizon = body.get("horizon", "")
        severity = body.get("severity", "")
        model_used = body.get("model_used", "unknown")
        response_preview = body.get("response_preview", "")[:200]
        
        # Get IP address
        # Vercel and other proxies usually put the client IP first in x-forwarded-for
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Handle list like "103.21.244.0, 10.0.0.1" -> take the first one
            ip_address = forwarded_for.split(",")[0].strip()
        else:
            # Fallback to direct client host
            ip_address = request.client.host if request.client else "unknown"

        with get_db_connection() as conn:
            if conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO queries (user_text, horizon, severity, model_used, response_preview, ip_address) VALUES (%s, %s, %s, %s, %s, %s)",
                    (text, horizon, severity, model_used, response_preview, ip_address)
                )
                conn.commit()
                cursor.close()
        return JSONResponse(content={"status": "logged"})
    except Exception as e:
        print(f"Logging error: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

# Endpoint to get query history
@app.get("/api/history")
async def get_history(request: Request, limit: int = 20):
    try:
        # Get IP address
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            ip_address = forwarded_for.split(",")[0].strip()
        else:
            ip_address = request.client.host if request.client else "unknown"

        with get_db_connection() as conn:
            if not conn:
                return JSONResponse(content={"queries": []})
            
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                "SELECT id, user_text, horizon, severity, model_used, created_at FROM queries WHERE ip_address = %s ORDER BY created_at DESC LIMIT %s",
                (ip_address, limit)
            )
            queries = cursor.fetchall()
            cursor.close()
            
            # Convert datetime to ISO format
            for q in queries:
                if q['created_at']:
                    q['created_at'] = q['created_at'].isoformat()
            
            return JSONResponse(content={"queries": queries})
    except Exception as e:
        print(f"History fetch error: {e}")
        return JSONResponse(content={"queries": [], "error": str(e)})
