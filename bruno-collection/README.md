# TailorBlend Backend API - Bruno Collection

Complete API collection for testing the TailorBlend AI supplement consultation backend.

## What is Bruno/Insomnium?

[Bruno](https://www.usebruno.com/) and [Insomnium](https://github.com/ArchGPT/insomnium) are open-source API clients (alternatives to Postman) that store collections as plain text files in your repository.

**Benefits**:
- ✅ Collections stored in Git (version controlled)
- ✅ No cloud sync or account required
- ✅ Offline-first design
- ✅ Team collaboration via Git
- ✅ Environment variables per environment

## Installation

### Bruno (Official)
```bash
# macOS
brew install bruno

# Windows
winget install Bruno

# Linux
# Download from https://www.usebruno.com/downloads
```

### Insomnium (Fork with enhanced features)
```bash
# macOS
brew install insomnium

# Windows/Linux
# Download from https://github.com/ArchGPT/insomnium/releases
```

## Opening the Collection

1. Launch Bruno or Insomnium
2. Click "Open Collection"
3. Navigate to: `tailorblend-backend-api/bruno-collection/`
4. Select the folder (don't select a specific file)

## Environments

### Local Development
- **Base URL**: `http://localhost:5000`
- **Use when**: Running backend locally with `python -m backend.api`

### Production
- **Base URL**: `https://tailorblend-backend-api.fly.dev`
- **Use when**: Testing deployed API on fly.io

**Switch environments**: Click environment dropdown in top-right corner.

## Collection Structure

```
bruno-collection/
├── bruno.json                          # Collection metadata
├── collection.bru                      # Collection-level docs & headers
├── README.md                           # This file
├── environments/
│   ├── Local.bru                       # Local development (localhost:5000)
│   └── Production.bru                  # Production (fly.dev)
├── Health & Lifecycle/
│   ├── Root.bru                        # GET /
│   ├── Health Check.bru                # GET /health
│   └── Readiness Check.bru             # GET /api/ready
├── Chat/
│   ├── Stream Chat (GET - Simple).bru  # GET /api/chat/stream
│   ├── Stream Chat (POST).bru          # POST /api/chat/stream
│   └── Chat (Non-Streaming).bru        # POST /api/chat
├── Session Management/
│   ├── Get Session Stats.bru           # GET /api/session/stats
│   ├── Reset Session.bru               # POST /api/session/reset
│   ├── Get Traces.bru                  # GET /api/session/{id}/traces
│   └── Stream Traces (SSE).bru         # GET /api/session/{id}/traces/stream
├── Configuration/
│   ├── Get Instructions.bru            # GET /api/instructions
│   ├── Update Instructions.bru         # POST /api/instructions
│   └── Reset Instructions.bru          # POST /api/instructions/reset
└── Multi-Agent/
    └── Create Blend (Streaming).bru    # POST /api/multi-agent/stream
```

## Quick Start Workflows

### 1. Basic Health Check
```
1. Select "Local" environment
2. Run: Health & Lifecycle > Health Check
3. Expected: {"status": "ok"}
```

### 2. Simple Chat Conversation
```
1. Run: Chat > Stream Chat (GET - Simple)
2. Run: Session Management > Get Session Stats
3. Check token usage and ZAR cost
```

### 3. Advanced Chat with Files
```
1. Edit: Chat > Stream Chat (POST - With Attachments)
2. Replace base64_data with actual file content
3. Run request
4. Watch SSE streaming response
```

### 4. Multi-Agent Blend Creation
```
1. Run: Multi-Agent > Create Blend (Streaming)
2. Watch agent progress (SupplementSpecialist → FormulationSpecialist)
3. Receive final blend recommendation
```

## Environment Variables

Both environments define:

| Variable | Local | Production |
|----------|-------|------------|
| `base_url` | http://localhost:5000 | https://tailorblend-backend-api.fly.dev |
| `session_id` | `test-session-{{$randomUUID}}` | `prod-session-{{$randomUUID}}` |

**Auto-generated values**:
- `{{$randomUUID}}`: Generates unique session ID per request
- Bruno/Insomnium supports other generators: `{{$timestamp}}`, `{{$randomInt}}`, etc.

## Testing SSE Streams

**Note**: Bruno/Insomnium may not display Server-Sent Events (SSE) streams perfectly.

### Alternative Testing Methods

**Using curl**:
```bash
curl -N "http://localhost:5000/api/chat/stream?message=Hello&session_id=test123"
```

**Using httpie**:
```bash
http --stream GET "http://localhost:5000/api/chat/stream" message=="Hello" session_id=="test123"
```

**Using JavaScript (browser console)**:
```javascript
const source = new EventSource('http://localhost:5000/api/chat/stream?message=Hello&session_id=test123');
source.onmessage = (event) => {
  console.log('Token:', event.data);
};
```

## Request Examples

### Chat with Custom Model
```json
POST /api/chat
{
  "message": "What supplements help with sleep?",
  "session_id": "my-session-123",
  "model": "gpt-5-nano-2025-08-07",
  "custom_instructions": "Be very concise. Use bullet points.",
  "practitioner_mode": false
}
```

### Chat with File Attachment
```json
POST /api/chat/stream
{
  "message": "Analyze this blood test",
  "session_id": "my-session-123",
  "attachments": [
    {
      "filename": "bloodwork.pdf",
      "base64_data": "JVBERi0xLjQK...",
      "mime_type": "application/pdf",
      "file_size": 45678
    }
  ]
}
```

### Multi-Agent Blend
```json
POST /api/multi-agent/stream
{
  "session_id": "my-session-123",
  "patient_profile": {
    "age": 28,
    "gender": "male",
    "weight_kg": 75,
    "height_cm": 180,
    "activity_level": "active",
    "health_goals": ["Build muscle", "Improve recovery"],
    "dietary_preferences": "omnivore",
    "current_medications": [],
    "allergies": ["shellfish"],
    "health_conditions": [],
    "lifestyle_factors": {
      "stress_level": "moderate",
      "sleep_hours": 7,
      "exercise_frequency": "5-6 times per week"
    }
  }
}
```

## Cost Tracking

All chat responses include ZAR cost calculation:

```json
{
  "response": "...",
  "tokens": {
    "input_tokens": 150,
    "output_tokens": 350,
    "total_tokens": 500
  },
  "cost_zar": 2.45,
  "model": "gpt-4.1-mini-2025-04-14"
}
```

**Model Pricing** (per 1M tokens, in ZAR @ 17.50 exchange rate):

| Model | Input (ZAR) | Output (ZAR) |
|-------|-------------|--------------|
| gpt-4.1-mini-2025-04-14 | R7.00 | R28.00 |
| gpt-5-mini-2025-08-07 | R4.38 | R35.00 |
| gpt-5-nano-2025-08-07 | R0.88 | R7.00 |
| gpt-5-chat-latest | R21.88 | R175.00 |

## Common Issues

### "Connection refused" on Local environment

**Problem**: Backend not running
**Solution**:
```bash
cd tailorblend-backend-api
python -m backend.api
```

### "Application is still initializing" from /api/ready

**Problem**: Heavy OpenAI SDK initialization in progress
**Solution**: Wait 10-30 seconds, then retry. `/health` always works.

### SSE stream not displaying

**Problem**: Bruno/Insomnium SSE rendering
**Solution**: Use curl/httpie (see "Testing SSE Streams" section)

### Session stats show zero

**Problem**: Wrong session ID or session doesn't exist
**Solution**: Use same `session_id` for all related requests. Check environment variable.

## Development Tips

### Persist Session ID

To keep same session across multiple requests:

1. Run any chat request
2. Copy `session_id` from response
3. In environment settings, replace:
   ```
   session_id: test-session-abc123-fixed
   ```
4. All requests now use same session

### Export Collection

```bash
# Bruno collections are already in Git!
git add bruno-collection/
git commit -m "Add API test collection"
git push
```

### Share with Team

```bash
# Team members just clone and open
git clone <repo>
cd tailorblend-backend-api/bruno-collection
# Open in Bruno/Insomnium
```

## Advanced Usage

### Pre-request Scripts

Bruno supports JavaScript pre-request scripts:

```javascript
// Example: Generate timestamp
bru.setVar("timestamp", Date.now());
```

### Tests/Assertions

```javascript
// Example: Verify response
expect(res.status).to.equal(200);
expect(res.body.status).to.equal("ok");
```

### Environment Secrets

For sensitive values (API keys):

1. Create `.env` file in collection folder (gitignored)
2. Reference in environments: `{{OPENAI_API_KEY}}`

## Resources

- **Bruno Documentation**: https://docs.usebruno.com/
- **Insomnium Repository**: https://github.com/ArchGPT/insomnium
- **TailorBlend Backend Docs**: See `backend/CLAUDE.md`
- **API Source Code**: See `backend/api.py`

## Support

Questions or issues with the collection?

1. Check request documentation (click "Docs" tab in Bruno)
2. Verify environment is correct (Local vs Production)
3. Check backend logs: `python -m backend.api`
4. Review `backend/api.py` for endpoint details

---

**Collection Version**: 1.0.0
**Last Updated**: 2025-01-19
**Maintained By**: TailorBlend Development Team
