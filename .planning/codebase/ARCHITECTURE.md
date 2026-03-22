# Architecture

**Analysis Date:** 2026-03-22

## Pattern Overview

**Overall:** Three-Agent Pipeline with Fallback-First Design

**Key Characteristics:**
- Message flows through discrete agents (Listener → Strategist → Closer) with clear separation of concerns
- Heuristic fallback at every LLM boundary—no single point of failure
- Async/await throughout for non-blocking I/O with FastAPI
- Protocol-driven LLM abstraction (duck typing) allows swap implementations
- JSON-based storage (MVP) with index caching for fast lead lookups

## Layers

**Request/API Layer:**
- Purpose: HTTP entry points for message processing and lead management
- Location: `main.py` (FastAPI app + endpoints), `integrations/zalo_routes.py` (webhook handlers)
- Contains: Route handlers, request/response models, dependency injection
- Depends on: All agents, storage (LeadStore, ConversationHistory), optional LLM
- Used by: Zalo webhook, internal tools, client dashboards

**Agent Layer:**
- Purpose: Business logic orchestration—extraction, strategy, reply generation
- Location: `agents/listener.py`, `agents/strategist.py`, `agents/closer.py`
- Contains: Agent classes with decision logic, both async and sync methods
- Depends on: Core models, storage, optional LLM provider
- Used by: Main request handler, webhook handler

**Core/Logic Layer:**
- Purpose: Domain models, heuristic extraction, LLM provider abstraction
- Location: `core/models.py` (dataclasses), `core/vietnamese_nlp.py` (heuristics), `core/llm/` (LLM boundary)
- Contains:
  - `LeadProfile`, `Message`, `Suggestion`, `FollowUpTask` (dataclasses for serialization)
  - `VietnameseExtractor` (regex-based fallback)
  - `LLMProvider` protocol + `AnthropicLLMProvider` implementation
  - Pydantic schemas for LLM I/O (`MessageExtraction`, `SuggestionOutput`)
- Depends on: External (anthropic library), no internal agent dependencies
- Used by: All agents, storage layer

**Storage Layer:**
- Purpose: Persistent state for leads and conversations
- Location: `core/memory.py`
- Contains:
  - `LeadStore` (JSON files under `data/leads/`, with in-memory index cache)
  - `ConversationHistory` (JSONL append-only per lead under `data/conversations/`)
- Depends on: Core models (for serialization), pathlib, json
- Used by: All agents, request handlers

**Integration Layer:**
- Purpose: External service communication (Zalo API)
- Location: `integrations/zalo_client.py`, `integrations/zalo_routes.py`
- Contains:
  - `ZaloClient` (message sending, webhook verification, OAuth)
  - `ZaloAuthManager` (multi-broker token management)
  - Webhook route handlers
- Depends on: httpx (async HTTP), core models, storage
- Used by: Webhook endpoint, manual send operations

## Data Flow

**Main Processing Pipeline (POST /process):**

1. **Request arrives** → `MessageRequest` model (lead_id, message, is_broker flag)
2. **Listener agent processes**:
   - Saves message to conversation history
   - If broker message: return early (skip extraction)
   - If customer message: extract using LLM (with VietnameseExtractor fallback)
   - Merge extracted data into existing lead profile or create new profile
   - Save updated profile to LeadStore
3. **Strategist agent decides action**:
   - Load lead profile from store
   - Check for unanswered questions (heuristic: "?" in last customer msg)
   - Check hours since last contact against FOLLOW_UP_INTERVALS (HOT=2h, WARM=24h, COLD=72h)
   - Return action recommendation: quick_reply | follow_up | gentle_nudge | wait
4. **Closer agent generates suggestions** (if action requires response):
   - Select tactics based on approach + interest level
   - If LLM available: async call to generate_suggestions (with conversation history context)
   - Fall back to template-based generation if LLM fails or unavailable
   - Return 3 ranked suggestions with confidence scores
5. **Response returned** → ProcessResponse with full analysis

**Webhook Flow (Zalo integration):**

1. Zalo POSTs message to `/zalo/webhook`
2. Verify signature using HMAC-SHA256 (app_secret)
3. Parse webhook payload, extract user_id and text
4. Get broker's authenticated client from auth manager
5. Call main pipeline with extracted lead_id
6. If suggestions generated: send top suggestion back via Zalo API
7. Log interaction

**State Management:**

- **Leads**: Stored as individual JSON files (`data/leads/{lead_id}.json`), indexed in-memory for fast lookups
- **Conversations**: Append-only JSONL per lead (`data/conversations/{lead_id}.jsonl`), read on-demand for context
- **Tokens**: OAuth tokens cached in `data/zalo_tokens.json` (one token per broker)
- **Index**: `data/leads/index.json` maintains counters (total, hot, warm, cold) updated on every save

## Key Abstractions

**LeadProfile:**
- Purpose: Unified lead state (budget, locations, interest level, history)
- Examples: `core/models.py:LeadProfile`
- Pattern: Mutable dataclass with `to_dict()` / `from_dict()` for JSON serialization
- Updated by: Listener (on each message), Strategist (on decision)

**Agent:**
- Purpose: Stateless processors that apply business rules to profiles and messages
- Examples: `ListenerAgent`, `StrategistAgent`, `CloserAgent`
- Pattern: Injected with storage + optional LLM provider at init; methods are async-aware
- Responsibility: Each agent owns one concern (extract | decide | generate)

**LLMProvider Protocol:**
- Purpose: Abstraction for Claude integration; enables heuristic fallback
- Examples: `core/llm/provider.py:LLMProvider` (Protocol), `AnthropicLLMProvider` (implementation)
- Pattern: `@runtime_checkable` protocol allows duck typing; methods are async
- Methods: `extract_message()`, `generate_suggestions()`

**Store Classes:**
- Purpose: Persistence with local caching
- Examples: `LeadStore`, `ConversationHistory`
- Pattern: LeadStore maintains counter cache; ConversationHistory appends for append-only durability

## Entry Points

**POST /process:**
- Location: `main.py:process_message()`
- Triggers: HTTP request from client/broker frontend
- Responsibilities: Orchestrate three agents, catch exceptions, return full analysis

**POST /zalo/webhook:**
- Location: `integrations/zalo_routes.py:zalo_webhook()`
- Triggers: Incoming message from Zalo Official Account
- Responsibilities: Verify signature, parse payload, call pipeline, send reply

**GET /lead/{lead_id}:**
- Location: `main.py:get_lead()`
- Triggers: Client requests lead profile + recent conversation
- Responsibilities: Load profile and recent messages from storage

**GET /leads/hot:**
- Location: `main.py:get_hot_leads()`
- Triggers: Client requests all hot leads
- Responsibilities: Query store for hot leads, return list

**GET /follow-ups?hours=24:**
- Location: `main.py:get_follow_ups()`
- Triggers: Client requests follow-up task list
- Responsibilities: Calculate follow-up tasks from all leads using Strategist

## Error Handling

**Strategy:** Graceful degradation with fallback to heuristics; log all failures; return sensible defaults

**Patterns:**

- **LLM call fails**: Log warning, fall back to VietnameseExtractor (Listener) or templates (Closer)
- **Webhook signature invalid**: Return 401 Unauthorized
- **Lead not found**: Return 404 Not Found (for GET /lead/)
- **Storage I/O fails**: Log error, return False or None; gracefully degrade
- **Missing environment variables**: Log info, continue in heuristic-only mode (no LLM calls)

**Logging:**

- All agents log at INFO level (startup messages, decisions)
- Failures log at WARNING (fallback triggered) or ERROR (unrecoverable issue)
- Module logger: `logging.getLogger(__name__)` in each file

## Cross-Cutting Concerns

**Logging:**
- Approach: Python `logging` module with module-level loggers
- Patterns: Log agent decisions, LLM calls, storage operations, errors
- Config: `logging.basicConfig(level=logging.INFO)` in `main.py`

**Validation:**
- Approach: Pydantic models for HTTP requests/responses; dataclass fields for domain models
- Patterns: Type hints throughout; explicit None checks before accessing optional fields
- Risk areas: Budget calculations, location matching (heuristic can over-match)

**Authentication:**
- Approach: HMAC-SHA256 webhook signature verification; OAuth tokens for Zalo API
- Implementation: `ZaloClient.verify_webhook()`, `ZaloAuthManager` for token management
- Note: No broker authentication on /process endpoint—trusted internal call

**Async Handling:**
- Approach: `async/await` for I/O-bound operations (LLM, HTTP, file operations)
- Pattern: ListenerAgent and CloserAgent have async methods; called with `await` from FastAPI
- Note: VietnameseExtractor and StrategistAgent are sync (no external I/O)

---

*Architecture analysis: 2026-03-22*
