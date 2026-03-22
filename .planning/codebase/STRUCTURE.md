# Codebase Structure

**Analysis Date:** 2026-03-22

## Directory Layout

```
zalo-ai-broker/
├── agents/                    # Three agent classes (Listener, Strategist, Closer)
│   ├── listener.py           # Extract data from messages
│   ├── strategist.py         # Decide next action
│   ├── closer.py             # Generate reply suggestions
│   └── __init__.py
├── core/                      # Domain models, heuristics, LLM abstraction
│   ├── models.py             # Dataclasses (LeadProfile, Message, Suggestion, FollowUpTask)
│   ├── vietnamese_nlp.py     # Heuristic extractors (regex-based fallback)
│   ├── memory.py             # Storage layer (LeadStore, ConversationHistory)
│   ├── llm/                  # LLM provider abstraction and Anthropic implementation
│   │   ├── provider.py       # LLMProvider Protocol and AnthropicLLMProvider
│   │   ├── schemas.py        # Pydantic models for LLM boundaries
│   │   ├── tools.py          # System prompts, tool schemas, message builders
│   │   └── __init__.py
│   └── __init__.py
├── integrations/              # External service integration (Zalo)
│   ├── zalo_client.py        # Zalo Official Account API client
│   ├── zalo_routes.py        # FastAPI webhook routes for Zalo
│   └── __init__.py
├── data/                      # Runtime storage (gitignored)
│   ├── leads/                # Individual lead profiles as JSON files
│   │   ├── {lead_id}.json    # Single lead profile
│   │   └── index.json        # Cached statistics (counters)
│   ├── conversations/        # Conversation history (append-only JSONL per lead)
│   │   └── {lead_id}.jsonl   # Messages in chronological order
│   └── zalo_tokens.json      # OAuth tokens per broker
├── tests/                     # Test suite
│   ├── test_basic.py         # Unit tests for extractors, agents, storage
│   └── __init__.py
├── main.py                    # FastAPI application, initialization, endpoints
├── example_usage.py           # Demo of processing a message (non-HTTP)
├── requirements.txt           # Python dependencies
├── runtime.txt                # Python version pinning (3.11.9)
├── Procfile                   # Railway deployment config
├── CLAUDE.md                  # Developer guide (this project)
├── README.md                  # Project overview
├── ZALO_SETUP_GUIDE.md       # Zalo integration instructions
├── DEPLOY_RAILWAY.md         # Railway deployment guide
└── QUICKSTART_ZALO.md        # Quick-start tutorial
```

## Directory Purposes

**agents/**
- Purpose: Three specialized agents for the pipeline
- Contains: Agent classes with business logic (extraction, strategy, reply generation)
- Key files: `listener.py`, `strategist.py`, `closer.py`

**core/**
- Purpose: Core domain, heuristics, and LLM provider abstraction
- Contains:
  - `models.py`: Dataclasses for all domain entities
  - `vietnamese_nlp.py`: Regex-based Vietnamese text processing fallback
  - `memory.py`: JSON-based storage (LeadStore, ConversationHistory)
  - `llm/`: Claude integration with fallback support

**integrations/**
- Purpose: External service integration
- Contains:
  - `zalo_client.py`: Zalo Official Account API wrapper
  - `zalo_routes.py`: FastAPI webhook routes for Zalo messages

**data/**
- Purpose: Runtime state storage (gitignored, created on startup)
- Contains:
  - `leads/`: Lead profiles (one JSON per lead) + index
  - `conversations/`: Append-only message logs (JSONL per lead)
  - `zalo_tokens.json`: OAuth token cache

**tests/**
- Purpose: Unit test suite
- Contains: Tests for heuristic extraction, agents, storage, LLM fallback
- Run with: `pytest tests/ -v`

## Key File Locations

**Entry Points:**
- `main.py`: FastAPI application, all HTTP endpoints, agent initialization
- `integrations/zalo_routes.py`: Zalo webhook entry point (when integrated)

**Configuration:**
- `.env` (runtime, not in repo): ANTHROPIC_API_KEY, ZALO_APP_ID, etc.
- `requirements.txt`: Python package dependencies
- `runtime.txt`: Python version (3.11.9)
- `Procfile`: Railway deployment entry point

**Core Logic:**
- `core/models.py`: LeadProfile, Message, Suggestion, FollowUpTask
- `core/vietnamese_nlp.py`: Budget, location, intent extraction (heuristic)
- `core/memory.py`: LeadStore, ConversationHistory persistence
- `core/llm/provider.py`: LLMProvider Protocol, AnthropicLLMProvider implementation
- `core/llm/schemas.py`: Pydantic models for LLM I/O (MessageExtraction, SuggestionOutput)
- `core/llm/tools.py`: System prompts, tool schemas, message builders for Claude API

**Agents:**
- `agents/listener.py`: Extract data from messages (LLM + heuristic fallback)
- `agents/strategist.py`: Decide next action (follow-up timing, urgency)
- `agents/closer.py`: Generate reply suggestions (LLM + template fallback)

**Integration:**
- `integrations/zalo_client.py`: ZaloClient, ZaloAuthManager for Zalo API
- `integrations/zalo_routes.py`: Webhook handler and message routing

**Testing:**
- `tests/test_basic.py`: Unit tests (extractors, agents, storage)

## Naming Conventions

**Files:**
- Source: `lowercase_with_underscores.py` (e.g., `listener.py`, `zalo_client.py`)
- Dataclasses in single files: `models.py`, `schemas.py`
- Agent files: `{agent_name}.py` (listener, strategist, closer)

**Directories:**
- Feature packages: `{feature}/` (agents, integrations, core, tests)
- Sub-packages: `{parent}/{child}/` (core/llm)
- Data/runtime: `data/{entity_type}/` (leads, conversations)

**Classes:**
- PascalCase: `ListenerAgent`, `CloserAgent`, `LeadProfile`, `ZaloClient`
- Enum: `PascalCase` (Intent, InterestLevel, IntentLevel)

**Functions/Methods:**
- camelCase for private methods: `_extract_information()`, `_merge_profile()`
- snake_case for public methods: `process_message()`, `get_hot_leads()`

**Variables:**
- snake_case for all variables: `lead_id`, `budget_min`, `llm_provider`
- Constants: UPPERCASE_WITH_UNDERSCORES: `FOLLOW_UP_INTERVALS`, `HOT_SIGNALS`

**Environment Variables:**
- UPPERCASE_WITH_UNDERSCORES: `ANTHROPIC_API_KEY`, `ZALO_APP_ID`, `ZALO_ACCESS_TOKEN`, `DEFAULT_BROKER_ID`

## Where to Add New Code

**New Feature (end-to-end):**
- Primary logic: Create in `core/` if shared, or in relevant `agents/` if agent-specific
- HTTP endpoint: Add route to `main.py` or create new router file and include in `main.py`
- Tests: Add class/method to `tests/test_basic.py`
- Example: New extraction signal → `core/vietnamese_nlp.py` (heuristic) + test case

**New Agent/Module:**
- Implementation: Create `agents/{agent_name}.py` (class inherits business logic pattern)
- Initialization: Inject in `main.py` with dependencies (storage, llm_provider)
- Async calls: Use `async def` if I/O-bound; sync if pure logic
- Example: New recommendation agent → `agents/recommender.py`, init in main, test in test_basic.py

**New External API Integration:**
- Client: Create `integrations/{service}_client.py` (follow ZaloClient pattern)
- Routes (if webhook): Create `integrations/{service}_routes.py`, include in `main.py`
- Example: Shopee integration → `integrations/shopee_client.py` + `integrations/shopee_routes.py`

**Utilities/Helpers:**
- Shared helpers: Add to existing `core/` module if domain-related; create `utils/` if generic
- Vietnamese-specific: Extend `core/vietnamese_nlp.py`
- LLM-related: Extend `core/llm/tools.py` (prompts, schemas) or `core/llm/provider.py` (provider logic)

**Tests:**
- Unit: Add test class/method to `tests/test_basic.py`
- Async test: Use `@pytest.mark.asyncio` decorator, write as `async def test_...`
- Mocking: Use `unittest.mock.AsyncMock` for async calls, `MagicMock` for sync
- Example: New agent test → `class TestNewAgent:` with setup_method and async test methods

## Special Directories

**data/**
- Purpose: Runtime storage (leads, conversations, tokens)
- Generated: Yes (created on startup by LeadStore/ConversationHistory)
- Committed: No (gitignored)
- Retention: Persists across restarts; manual cleanup required for testing

**core/llm/**
- Purpose: LLM provider abstraction (Claude integration)
- Contents:
  - `provider.py`: Protocol + AnthropicLLMProvider class
  - `schemas.py`: Pydantic models for LLM boundaries (MessageExtraction, SuggestionOutput)
  - `tools.py`: System prompts (Vietnamese), tool schemas, message builders
- Pattern: Separates Pydantic validation (schemas) from business logic (provider)

**tests/**
- Purpose: Unit test suite
- Structure: One test class per component (TestVietnameseExtractor, TestListenerAgent, etc.)
- Run: `pytest tests/ -v` or `pytest tests/test_basic.py::TestClassName -v`
- Fixtures: Use `setup_method()` for per-test initialization; no test data files committed

## Code Organization Patterns

**Agent Pattern:**
```python
class {Agent}Agent:
    def __init__(self, storage, optional_llm_provider=None):
        # Inject dependencies

    async def public_entry_point(self, inputs):
        # Main async API

    async def _async_helper(self):
        # Private async if needed

    def _sync_helper(self):
        # Private sync logic
```

**LLM Fallback Pattern:**
```python
if self._llm_provider is not None:
    try:
        result = await self._llm_provider.call(...)
        return result
    except Exception as exc:
        logger.warning("LLM failed, falling back to heuristic: %s", exc)

# Fallback (always available)
return self._fallback_method(...)
```

**Storage Read/Write:**
```python
# Read (LeadStore.get)
lead = self.lead_store.get(lead_id)
if not lead:
    return None  # Not found

# Write (LeadStore.save)
self.lead_store.save(updated_profile)  # Updates index counters
```

---

*Structure analysis: 2026-03-22*
