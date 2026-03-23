# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Zalo AI Broker is a FastAPI backend that helps Vietnamese real estate brokers close deals faster. It processes customer messages in Vietnamese, qualifies leads, and generates personalized response suggestions using a three-agent architecture.

## Commands

```bash
# Run development server
uvicorn main:app --reload

# Run tests
pytest tests/ -v

# Run a single test
pytest tests/test_basic.py::TestVietnameseExtractor::test_budget_extraction_range -v

# Format code
black .

# Lint
flake8 .
```

## Environment Setup

Copy `.env.example` to `.env` and fill in:
```
ZALO_APP_ID=...
ZALO_APP_SECRET=...
ZALO_ACCESS_TOKEN=...
ZALO_VERIFY_TOKEN=zalo_broker_assistant_2026
DEFAULT_BROKER_ID=...

# LLM (optional – heuristic fallback used when absent)
ANTHROPIC_API_KEY=...
# ANTHROPIC_MODEL_EXTRACTION=claude-haiku-4-5-20251001   (default)
# ANTHROPIC_MODEL_REPLY=claude-haiku-4-5-20251001        (default)
```

## Architecture

The app is built around a **three-agent pipeline** in `main.py`:

```
Customer message (Vietnamese)
    → ListenerAgent   → extracts budget, location, intent, interest level; updates lead profile
    → StrategistAgent → decides action (quick_reply / follow_up / gentle_nudge / wait)
    → CloserAgent     → generates 3 persuasive Vietnamese message options
```

**Agents** (`agents/`):
- `listener.py` — async; extracts structured data from raw messages via LLM (Claude Haiku) with heuristic fallback; classifies leads HOT/WARM/COLD
- `strategist.py` — applies follow-up timing rules (HOT=2h, WARM=24h, COLD=72h) to recommend the next action
- `closer.py` — async; generates personalized Vietnamese reply suggestions via LLM with template fallback; tactics: urgency, scarcity, social proof, value, soft touch

**Core** (`core/`):
- `vietnamese_nlp.py` — rule-based heuristic extractor; fallback when LLM is unavailable
- `models.py` — plain Python dataclasses: `LeadProfile`, `Message`, `Suggestion`, `FollowUpTask`
- `memory.py` — JSON-based storage; leads in `data/leads/{lead_id}.json`, conversations in `data/conversations/{lead_id}.jsonl`
- `llm/provider.py` — `LLMProvider` Protocol + `AnthropicLLMProvider` (uses `anthropic.AsyncAnthropic`; 1 retry on rate-limit/5xx; both agents share one instance)
- `llm/schemas.py` — Pydantic I/O types for LLM boundary: `MessageExtraction`, `SuggestionOutput`
- `llm/tools.py` — Anthropic tool schemas, Vietnamese system prompts, and message builders for extraction and reply calls

**Integrations** (`integrations/`):
- `zalo_client.py` — HTTP client for Zalo Official Account API (send messages, manage tokens)
- `zalo_routes.py` — FastAPI router for Zalo webhook verification and message receipt

**Key endpoints** in `main.py`:
- `POST /process` — main pipeline endpoint; takes `{lead_id, message, broker_id}`, returns full analysis + suggestions
- `GET /lead/{lead_id}` — lead profile + recent conversation
- `GET /leads/hot` — all hot leads
- `GET /follow-ups?hours=24` — leads needing follow-up
- `POST /zalo/webhook` / `GET /zalo/webhook` — Zalo integration
- `POST /zalo/send` — send a message to a lead via Zalo

## Data Storage

All state is in JSON files under `data/` (gitignored). This is intentional for MVP simplicity; a PostgreSQL migration is planned.

- `data/leads/{lead_id}.json` — `LeadProfile` objects
- `data/conversations/{lead_id}.jsonl` — one `Message` JSON per line
- `data/zalo_tokens.json` — broker OAuth tokens

## Deployment

Deployed to Railway. Configuration is in `Procfile`:
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

Python version is pinned in `runtime.txt` (`python-3.11.9`). Detailed setup is in `DEPLOY_RAILWAY.md` and `ZALO_SETUP_GUIDE.md`.
