# External Integrations

**Analysis Date:** 2026-03-22

## APIs & External Services

**Zalo Official Account API:**
- Zalo messaging platform for Vietnamese users
  - SDK/Client: Custom `ZaloClient` class in `integrations/zalo_client.py`
  - Auth: OAuth access tokens stored per-broker in `data/zalo_tokens.json`
  - Endpoints:
    - `POST https://openapi.zalo.me/v2.0/oa/message` - Send text messages and quick replies to users
    - `GET https://openapi.zalo.me/v2.0/oa/getuser` - Fetch user profile information
  - Webhook: Incoming messages via `POST /zalo/webhook` (webhook verification via `GET /zalo/webhook`)
  - HMAC-SHA256 signature verification for webhook security using `X-Zalo-Signature` and `X-Zalo-Timestamp` headers

**Anthropic Claude API:**
- LLM for message extraction and reply generation
  - SDK/Client: `anthropic>=0.40.0` via `AsyncAnthropic` client in `core/llm/provider.py`
  - Auth: `ANTHROPIC_API_KEY` environment variable
  - Models: `claude-haiku-4-5-20251001` (configurable via `ANTHROPIC_MODEL_EXTRACTION`, `ANTHROPIC_MODEL_REPLY`, or `ANTHROPIC_MODEL`)
  - Tool use: Structured tool calling for extraction and suggestion generation
    - Extraction tool: `extract_lead_data` - returns `MessageExtraction` schema with budget, location, interest level, intent
    - Reply tool: `generate_reply_suggestions` - returns array of `SuggestionOutput` with message, tactics, reasoning
  - Retry strategy: 1 retry on `RateLimitError` or `InternalServerError` with 1-second delay (in `core/llm/provider.py`)
  - Fallback: Heuristic-only mode if `ANTHROPIC_API_KEY` not set; rule-based extraction in `core/vietnamese_nlp.py` used as fallback

## Data Storage

**Databases:**
- No dedicated database - MVP uses JSON file storage
  - Lead profiles: `data/leads/{lead_id}.json` - Persisted `LeadProfile` objects with counter cache
  - Conversation history: `data/conversations/{lead_id}.jsonl` - One JSON message per line
  - Zalo tokens: `data/zalo_tokens.json` - Multi-broker OAuth token storage
  - Index: `data/leads/index.json` - Statistics cache (total, hot, warm, cold lead counts)
- Future migration to PostgreSQL planned (noted in `core/memory.py`)

**File Storage:**
- Local filesystem only - no cloud storage integration

**Caching:**
- In-memory counter cache in `LeadStore._counters` - Avoids O(n) rebuilds on every save
- HTTP client instances created per-request (httpx.AsyncClient in context managers)

## Authentication & Identity

**Auth Provider:**
- Custom OAuth implementation via `ZaloAuthManager` class
  - Handles multi-broker OAuth token storage in `data/zalo_tokens.json`
  - Each broker authenticated with Zalo via OAuth flow
  - Access tokens persisted with refresh tokens and `updated_at` timestamp
  - No user authentication layer - broker-focused system

**Zalo Webhook Verification:**
- Token-based: `ZALO_VERIFY_TOKEN` environment variable (set to `zalo_broker_assistant_2026` in `.env.example`)
- HMAC-SHA256 signature verification for all incoming webhooks using app secret

## Monitoring & Observability

**Error Tracking:**
- Not integrated - errors logged via Python standard logging

**Logs:**
- Python standard `logging` module configured in `main.py` with INFO level
- Logged to stderr; no external log aggregation

## CI/CD & Deployment

**Hosting:**
- Railway platform
- Procfile-based: `web: uvicorn main:app --host 0.0.0.0 --port $PORT`
- Environment variables configured in Railway dashboard

**CI Pipeline:**
- Not detected - no GitHub Actions, GitLab CI, or similar configured

## Environment Configuration

**Required env vars:**
- `ZALO_APP_ID` - Zalo Official Account app ID from https://developers.zalo.me/
- `ZALO_APP_SECRET` - Zalo app secret
- `ZALO_ACCESS_TOKEN` - Initial OAuth access token (can be refreshed)
- `ZALO_VERIFY_TOKEN` - Token for webhook verification (default: `zalo_broker_assistant_2026`)
- `ANTHROPIC_API_KEY` - Claude API key (optional; heuristic fallback used if absent)
- `DEFAULT_BROKER_ID` - Broker identifier for single-broker testing

**Optional env vars:**
- `ANTHROPIC_MODEL_EXTRACTION` - Model for extraction (defaults to `claude-haiku-4-5-20251001`)
- `ANTHROPIC_MODEL_REPLY` - Model for reply generation (defaults to `claude-haiku-4-5-20251001`)
- `ANTHROPIC_MODEL` - Single override for both extraction and reply models
- `HOST` - Server host binding (default: 0.0.0.0)
- `PORT` - Server port (default: 8000)

**Secrets location:**
- `.env` file (development) - Created by copying `.env.example`
- Railway environment variables (production)

## Webhooks & Callbacks

**Incoming:**
- `GET /zalo/webhook` - Zalo verification endpoint (query params: `hub_mode`, `hub_challenge`, `hub_verify_token`)
- `POST /zalo/webhook` - Zalo message delivery webhook (receives `user_send_text` events with signature verification)

**Outgoing:**
- Zalo API calls to send messages back to users:
  - Text messages: `POST https://openapi.zalo.me/v2.0/oa/message`
  - Messages with quick reply suggestions (up to 3 per message)
- No outbound webhooks to third-party services detected

---

*Integration audit: 2026-03-22*
