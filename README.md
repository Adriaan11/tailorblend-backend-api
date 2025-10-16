# TailorBlend AI Consultant - Backend API

**Python FastAPI + OpenAI Agents SDK**

Standalone backend service for the TailorBlend supplement consultation platform. Provides SSE streaming API for real-time AI-powered supplement recommendations.

## Overview

This is the **independent backend API** that was split from the monorepo. It runs separately from the Blazor frontend and communicates via HTTP/SSE.

- **Framework**: FastAPI (Python 3.11)
- **AI**: OpenAI Agents SDK with file_search tool
- **Database**: Vector store with 111 ingredients + 4 base mix types
- **Communication**: Server-Sent Events (SSE) for token-by-token streaming
- **Port**: 5000 (local dev), 8080 (production)

## Architecture

```
Blazor Frontend (separate repo)
    ↓ HTTP + SSE
Python FastAPI Backend (this repo)
    ↓ API calls
OpenAI API (GPT-4 mini + file_search tool)
    ↓ Queries
Vector Store (ingredients + base mixes)
```

## Quick Start

### 1. Prerequisites

- Python 3.11+
- OpenAI API key: https://platform.openai.com/api-keys

### 2. Installation

```bash
# Clone repository
git clone <backend-repo-url>
cd tailorblend-backend-api

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r backend/requirements-api.txt
```

### 3. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=sk-...
```

### 4. Run Locally

```bash
# Start API server (runs on http://localhost:5000)
python -m backend.api

# Or with uvicorn directly
uvicorn backend.api:app --host 0.0.0.0 --port 5000 --reload
```

### 5. Test Health

```bash
curl http://localhost:5000/api/health
# Should return: {"status": "ok", "service": "tailorblend-ai-consultant-api", "version": "1.0.0"}
```

## API Endpoints

### Core Consultation

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/health` | GET | Health check |
| `/api/chat/stream` | GET | Stream chat (text-only, backward compatible) |
| `/api/chat/stream` | POST | Stream chat (supports file attachments) |
| `/api/session/stats` | GET | Get token usage & cost for session |
| `/api/session/reset` | POST | Clear conversation history |

### Configuration

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/instructions` | GET | Get current system instructions |
| `/api/instructions` | POST | Update system instructions |
| `/api/instructions/reset` | POST | Reset to default instructions |

### Advanced

| Endpoint | Method | Purpose |
| `/api/multi-agent/stream` | POST | Multi-agent blend formulation |

## Example Usage

### Chat with SSE Streaming

```bash
# GET endpoint (text-only)
curl "http://localhost:5000/api/chat/stream?message=I%27m%20always%20tired&session_id=abc123"

# POST endpoint (with file attachments)
curl -X POST http://localhost:5000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I am vegan and train hard",
    "session_id": "abc123",
    "attachments": []
  }'
```

### Get Session Stats

```bash
curl "http://localhost:5000/api/session/stats?session_id=abc123"
```

### Update Instructions

```bash
curl -X POST http://localhost:5000/api/instructions \
  -H "Content-Type: application/json" \
  -d '{
    "raw_text": "New instructions here..."
  }'
```

## Configuration

### System Instructions

Edit `spec/instructions.txt` to change agent behavior:

- **Consultation flow**: 4-phase process (registration → discovery → assessment → formulation)
- **Tone**: Professional, conversational, health-focused
- **Constraints**: Safety guidelines, ingredient interactions, dosage limits

For healthcare practitioners, use `spec/practitioner-instructions.txt`.

### Vector Store

Contains 111 ingredients + 4 base mix types (hardcoded):

```python
VECTOR_STORE_ID = "vs_68ee8e3a25a48191aa18ff9c1dddbc01"
```

Files in store:
- `ingredients-database.md` - All 111 supplements
- `base-add-mixes-database.md` - Base formulas & customizations

### CORS Configuration

For production, set `CORS_ALLOWED_ORIGINS` environment variable:

```bash
# Single origin
export CORS_ALLOWED_ORIGINS="https://ui.tailorblend.com"

# Multiple origins (comma-separated)
export CORS_ALLOWED_ORIGINS="https://ui.tailorblend.com,https://app.tailorblend.com"
```

Default allowed (always):
- `http://localhost:8080`
- `http://127.0.0.1:8080`

## Deployment

### Deploy to fly.io

```bash
# 1. Set OpenAI API key
fly secrets set OPENAI_API_KEY=sk-...your-key...

# 2. Set CORS for production frontend
fly secrets set CORS_ALLOWED_ORIGINS="https://ui.tailorblend.com"

# 3. Deploy
fly deploy

# 4. Monitor
fly status
fly logs
```

### Deploy to Railway

```bash
# 1. Connect GitHub repo
# 2. Add environment variables in Railway dashboard:
#    - OPENAI_API_KEY=sk-...
#    - CORS_ALLOWED_ORIGINS=https://ui.tailorblend.com
# 3. Railway auto-deploys on git push
```

### Deploy to Google Cloud Run

```bash
# Build and push to Cloud Registry
gcloud builds submit --tag gcr.io/PROJECT_ID/tailorblend-api

# Deploy
gcloud run deploy tailorblend-api \
  --image gcr.io/PROJECT_ID/tailorblend-api \
  --set-env-vars="OPENAI_API_KEY=sk-...,CORS_ALLOWED_ORIGINS=https://ui.tailorblend.com"
```

## Environment Variables

### Required

| Variable | Value | Example |
|----------|-------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key | `sk-...` |

### Optional

| Variable | Purpose | Default |
|----------|---------|---------|
| `CORS_ALLOWED_ORIGINS` | Allowed frontend origins | (none, localhost allowed) |
| `PYTHON_API_PORT` | Server port | `5000` |
| `ASPNETCORE_ENVIRONMENT` | Environment mode | `Development` |

## Project Structure

```
tailorblend-backend-api/
├── backend/
│   ├── api.py                    # FastAPI app with all endpoints
│   ├── models.py                 # Request/response models
│   └── requirements-api.txt      # Python dependencies
├── tb_agents/
│   ├── consultant.py             # Agent creation
│   └── multi_agent_orchestrator.py  # Multi-agent system
├── config/
│   └── settings.py               # Load prompts, vector store ID
├── spec/
│   ├── instructions.txt          # Consumer mode (source of truth)
│   ├── practitioner-instructions.txt  # Healthcare mode
│   ├── ingredients-database.md   # In vector store
│   └── base-add-mixes-database.md  # In vector store
├── instruction_parser.py         # Parse/reassemble instructions
├── token_counter.py              # Token counting & ZAR cost
├── Dockerfile                    # Production image
├── fly.toml                      # fly.io deployment config
├── .env.example                  # Environment template
└── README.md                     # This file
```

## Development

### Testing Locally

```bash
# In one terminal: Start API
python -m backend.api

# In another terminal: Test streaming
curl "http://localhost:5000/api/chat/stream?message=Test&session_id=test123"

# Or use the Gradio web interface (if available in monorepo)
python main_gradio.py  # Requires monorepo
```

### Making API Calls from Code

```python
import requests

# Stream chat response
response = requests.get(
    "http://localhost:5000/api/chat/stream",
    params={
        "message": "I'm tired and unfocused",
        "session_id": "user123"
    },
    stream=True
)

# Process SSE stream
for line in response.iter_lines():
    if line.startswith(b"data: "):
        token = line[6:].decode()
        print(token, end="", flush=True)
```

### Debugging

Enable verbose logging:

```bash
# Watch stderr for debug messages
python -m backend.api 2>&1 | grep -i "debug\|error\|\[api\]"
```

## Troubleshooting

### "OPENAI_API_KEY not found"

```bash
# Create .env file
cp .env.example .env

# Edit and add your API key
nano .env  # or use your editor

# Verify it's loaded
grep OPENAI_API_KEY .env
```

### "Instructions file not found"

```bash
# Verify spec directory exists
ls -la spec/instructions.txt

# Check you're in the repo root
pwd
```

### API returns 500 error

```bash
# Check logs for details
curl -v http://localhost:5000/api/health

# Look for error messages in stderr
```

### CORS blocked in browser

```bash
# Check allowed origins
curl -H "Origin: http://frontend.local" \
     -H "Access-Control-Request-Method: GET" \
     -H "Access-Control-Request-Headers: Content-Type" \
     http://localhost:5000/api/chat/stream

# Set CORS_ALLOWED_ORIGINS if needed
export CORS_ALLOWED_ORIGINS="http://frontend.local"
python -m backend.api
```

## Performance Tuning

### Token Counting

For accurate token counting, we use `tiktoken` (OpenAI's official tokenizer). Costs are calculated in ZAR (South African Rand).

```python
from token_counter import calculate_cost_zar

cost_info = calculate_cost_zar(input_tokens=1000, output_tokens=500)
# Returns: {"input_cost_zar": X, "output_cost_zar": Y, "total_cost_zar": Z}
```

### Vector Store Queries

The agent uses OpenAI's file_search tool to query ingredients and base mixes. No need to optimize - it's handled by OpenAI.

## Testing Scenarios

### Scenario 1: Energy & Focus
- Input: "I'm always tired and can't concentrate"
- Expected: B vitamins, CoQ10, L-theanine
- Base: Drink

### Scenario 2: Vegan Athlete
- Input: "I'm vegan and lift weights 4x/week"
- Expected: Vegan Shake + BCAAs + creatine
- Base: Shake (Vegan)

### Scenario 3: Sleep & Stress
- Input: "Can't sleep, stressed from work"
- Expected: Magnesium glycinate, L-theanine, GABA
- Base: Drink

## Contributing

When modifying the backend:

1. **System behavior**: Edit `spec/instructions.txt` (not code)
2. **API changes**: Update `backend/api.py` with clear docstrings
3. **New features**: Add tests and update this README
4. **Dependencies**: Run `pip freeze > backend/requirements-api.txt`

## Security

- No secrets in code (use .env or environment variables)
- API key stored in environment only (never logged)
- CORS restricted to authorized origins
- Non-root user in Docker (security best practice)
- Health checks every 30 seconds

## Support

For issues or questions:

1. Check this README's Troubleshooting section
2. Review `spec/instructions.txt` for agent behavior
3. Check OpenAI Agents SDK docs: https://openai.github.io/openai-agents-python/
4. File an issue in the repository

## License

See main TailorBlend project license.
