# Technology Stack

**Analysis Date:** 2026-03-22

## Languages

**Primary:**
- Python 3.11.9 - Main application language

## Runtime

**Environment:**
- Python 3.11.9 (pinned in `runtime.txt`)

**Package Manager:**
- pip - Installs dependencies from `requirements.txt`
- Lockfile: Not explicitly used (dependencies pinned by version in requirements.txt)

## Frameworks

**Core:**
- FastAPI 0.104.1 - Web framework for REST API endpoints and async request handling
- Uvicorn 0.24.0 - ASGI server for running FastAPI application; configured in `Procfile` for production

**Async/Runtime:**
- Python standard library asyncio - Async runtime for all async operations

**Testing:**
- pytest 7.4.3 - Test runner
- pytest-asyncio 0.23.0+ - Async test support; configured with `asyncio_mode = "auto"` in `pyproject.toml`

**Build/Dev:**
- black 23.12.0 - Code formatter
- flake8 6.1.0 - Linter

## Key Dependencies

**Critical:**
- anthropic >= 0.40.0 - Claude API client for LLM-powered message extraction and reply generation; uses `AsyncAnthropic` for non-blocking calls
- pydantic 2.5.0 - Data validation and serialization; used for LLM boundary types in `core/llm/schemas.py` and FastAPI request/response models
- python-dotenv 1.0.0 - Environment variable loading from `.env` file

**Infrastructure:**
- requests 2.31.0 - HTTP client library
- python-dateutil 2.8.2 - DateTime parsing and manipulation
- httpx - Async HTTP client used in `integrations/zalo_client.py` for Zalo API calls

## Configuration

**Environment:**
- `.env` file for local configuration
- Environment variables documented in `.env.example`:
  - Zalo API: `ZALO_APP_ID`, `ZALO_APP_SECRET`, `ZALO_ACCESS_TOKEN`, `ZALO_VERIFY_TOKEN`
  - LLM: `ANTHROPIC_API_KEY`, optional `ANTHROPIC_MODEL_EXTRACTION` and `ANTHROPIC_MODEL_REPLY` (defaults to `claude-haiku-4-5-20251001`)
  - Broker: `DEFAULT_BROKER_ID`
  - Server: `HOST` (default 0.0.0.0), `PORT` (default 8000)

**Build:**
- `Procfile` - Defines web process: `uvicorn main:app --host 0.0.0.0 --port $PORT` (Railway/Procfile-based deployment)
- `pyproject.toml` - pytest configuration with asyncio auto mode

## Platform Requirements

**Development:**
- Python 3.11.9
- pip package manager
- Standard POSIX environment (tested on darwin)

**Production:**
- Railway platform (configured via Procfile)
- Environment variables set in Railway dashboard for: Zalo credentials, Anthropic API key, broker ID, webhook token
- File system access for JSON-based data storage in `data/` directory

---

*Stack analysis: 2026-03-22*
