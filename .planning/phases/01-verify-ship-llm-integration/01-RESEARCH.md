# Phase 1: Verify & Ship LLM Integration - Research

**Researched:** 2026-03-22
**Domain:** Anthropic Python SDK (async), pytest-asyncio mocking, git staging
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LLM-01 | ListenerAgent uses Claude Haiku for extraction when `ANTHROPIC_API_KEY` is set | Code verified correct — `_extract_information` calls `llm_provider.extract_message`; provider uses `tool_choice={"type":"tool","name":"extract_lead_data"}` |
| LLM-02 | CloserAgent uses Claude Haiku for 3 personalized Vietnamese suggestions when key is set | Code verified correct — `generate_suggestions` calls `llm_provider.generate_suggestions`; provider uses `tool_choice={"type":"tool","name":"generate_reply_suggestions"}` |
| LLM-03 | Both agents fall back to heuristic/template mode transparently on LLM error or absence | Code verified correct — both agents wrap LLM calls in `try/except Exception` and fall back; `ListenerAgent` injects `None` when no provider |
| LLM-04 | `core/llm/` (provider, schemas, tools) is committed and tracked in git | Currently untracked — `git ls-files --others` shows all 4 files; staging required |
| TEST-01 | ListenerAgent LLM path covered by mocked tests | Tests exist and pass: `TestListenerLLMPath::test_llm_extraction_used`, `test_llm_failure_falls_back_to_heuristics` |
| TEST-02 | CloserAgent LLM path covered by mocked tests | Tests exist and pass: `TestCloserLLMPath::test_llm_suggestions_used`, `test_llm_failure_falls_back_to_templates` |
| TEST-03 | All existing tests continue to pass after integration commit | Verified: `pytest tests/ -v` → 13 passed, 0 failed (Python 3.13.3, pytest 9.0.2) |
| ENV-01 | `.env.example` documents `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL_EXTRACTION`, `ANTHROPIC_MODEL_REPLY` | Present and correct in working tree; modification is unstaged |
| ENV-02 | App logs which mode it starts in (LLM or heuristic-only) | Implemented in `main.py::_build_llm_provider()` — logs `"ANTHROPIC_API_KEY not set – running in heuristic-only mode"` or `"LLM provider: extraction=%s  reply=%s"` |
</phase_requirements>

---

## Summary

The LLM integration is architecturally complete and correct. All code exists in the working tree and all 13 tests pass right now. The only remaining work is operational: stage the untracked `core/llm/` directory, stage the modified files (agents, main.py, requirements.txt, tests, .env.example, pyproject.toml), and commit them as a single coherent unit.

No bugs were found in `provider.py`, `schemas.py`, or `tools.py`. The Anthropic SDK version installed (0.86.0) is compatible with all patterns used: `tool_choice={"type":"tool","name":"..."}` is the correct `ToolChoiceToolParam` format, `block.type == "tool_use"` correctly identifies `ToolUseBlock` objects, and `block.input` is a `Dict[str, object]` that can be spread into Pydantic constructors via `**`. Retry logic is correct — `range(2)` gives attempts 0 and 1, with sleep-and-continue on attempt 0 and re-raise on attempt 1 for `RateLimitError`/`InternalServerError`.

The test file already covers all four LLM requirement paths using `unittest.mock.AsyncMock` and `MagicMock`. The `pyproject.toml` sets `asyncio_mode = "auto"` which makes `pytest-asyncio` run async test methods automatically without any `@pytest.mark.asyncio` decorator. This is the correct configuration for the installed `pytest-asyncio==1.3.0`.

**Primary recommendation:** Stage and commit the six file groups in one clean commit. No code changes are required — everything is already correct.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| anthropic | 0.86.0 (installed); `>=0.40.0` pinned in requirements | Anthropic Messages API client | Official SDK; `AsyncAnthropic` avoids blocking FastAPI event loop |
| pydantic | 2.5.0 | Schema validation for LLM boundary types | Already project-wide; `MessageExtraction`, `SuggestionOutput` use `BaseModel` |
| pytest-asyncio | 1.3.0 (installed) | Async test runner | Required for `asyncio_mode="auto"` in `pyproject.toml` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| unittest.mock.AsyncMock | stdlib | Mock async coroutines | Used in all LLM path tests instead of real API calls |
| unittest.mock.MagicMock | stdlib | Mock sync attributes on provider objects | Used alongside `AsyncMock` for `provider.generate_suggestions` / `provider.extract_message` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `AsyncMock` (stdlib) | `pytest-mock` / `respx` | stdlib is sufficient for mocking the injected `LLMProvider` protocol; no HTTP interception needed |
| `tool_choice={"type":"tool","name":"..."}` | `tool_choice={"type":"any"}` | Forced tool use guarantees structured output; "any" allows free-text fallback which breaks schema parsing |

**Installation (already in requirements.txt):**
```bash
pip install anthropic>=0.40.0 pytest-asyncio>=0.23.0
```

---

## Architecture Patterns

### Recommended Project Structure
```
core/llm/
├── __init__.py      # empty marker (already exists)
├── provider.py      # LLMProvider Protocol + AnthropicLLMProvider
├── schemas.py       # Pydantic I/O boundary types
└── tools.py         # Anthropic tool schemas, system prompts, message builders
```

### Pattern 1: Dependency-Injected LLM Provider
**What:** `AnthropicLLMProvider` is constructed once at startup in `main.py::_build_llm_provider()` and injected into `ListenerAgent` and `CloserAgent` constructors. Both agents type-hint the parameter as `llm_provider=None` to avoid import cycles.
**When to use:** Any time you want the same provider instance shared across agents without creating circular imports.
**Example:**
```python
# main.py
llm_provider = _build_llm_provider()
listener = ListenerAgent(lead_store, conv_history, llm_provider=llm_provider)
closer = CloserAgent(llm_provider=llm_provider)
```

### Pattern 2: Try-LLM-Then-Fallback
**What:** Both agents wrap the LLM call in `try/except Exception` and fall back to rule-based logic on any failure.
**When to use:** Every LLM call that has a deterministic fallback.
**Example:**
```python
# agents/listener.py (verified correct)
if self._llm_provider is not None:
    try:
        extraction = await self._llm_provider.extract_message(text, history, ...)
        return { ... }  # convert extraction to dict
    except Exception as exc:
        logger.warning("LLM extraction failed, falling back: %s", exc)
# Heuristic fallback runs here
```

### Pattern 3: AsyncMock for LLM Provider Tests
**What:** Use `MagicMock()` as the provider shell, then assign `AsyncMock(return_value=...)` to async methods. Pass the mock as `llm_provider=provider` to the agent under test.
**When to use:** Every test that exercises an LLM code path without making real API calls.
**Example:**
```python
# tests/test_basic.py (verified working — all 13 tests pass)
provider = MagicMock()
provider.extract_message = AsyncMock(return_value=MessageExtraction(
    interest_level="hot", intent="buy", locations=["quận 2"],
    property_types=["apartment"], key_phrases=[], open_questions=[]
))
agent = ListenerAgent(lead_store, conv, llm_provider=provider)
result = await agent.process_message(...)
provider.extract_message.assert_awaited_once()
```

### Pattern 4: Tool-Use Forced Structured Output
**What:** Both `extract_message` and `generate_suggestions` pass `tool_choice={"type": "tool", "name": "<tool_name>"}` to force the model to always return the named tool call.
**When to use:** Any time you need schema-guaranteed JSON from the model rather than free-form text.
**Example:**
```python
# core/llm/provider.py (verified correct against SDK 0.86.0)
response = await self._client.messages.create(
    model=self._extraction_model,
    max_tokens=512,
    system=EXTRACTION_SYSTEM_PROMPT,
    tools=[EXTRACTION_TOOL],
    tool_choice={"type": "tool", "name": "extract_lead_data"},
    messages=messages,
)
for block in response.content:
    if block.type == "tool_use" and block.name == "extract_lead_data":
        return MessageExtraction(**block.input)
```

### Anti-Patterns to Avoid
- **Real API calls in tests:** Never instantiate `AnthropicLLMProvider` in tests — always mock the `LLMProvider` interface.
- **Importing `AnthropicLLMProvider` at module level in agents:** The agents use `llm_provider=None` typed as untyped to avoid this import cycle — do not add a top-level import.
- **Staging unrelated files:** `.cursor/` directory is untracked; do not include it in the LLM integration commit.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Structured output from LLM | Custom JSON-parsing of free-form text | `tool_choice={"type":"tool"}` + Pydantic | Forced tool use guarantees schema; free-form parsing breaks on any LLM variation |
| Async test execution | Manual `asyncio.run()` in tests | `asyncio_mode="auto"` in pyproject.toml | Already configured; adding `asyncio.run()` creates nested loop errors |
| HTTP mocking for Anthropic | `responses` / `httpx` intercept | `AsyncMock` on the injected provider | Provider is already injected; no HTTP layer to intercept |

**Key insight:** The injected-provider pattern (dependency injection, not global state) means tests never need to intercept HTTP — they just pass a mock object with the same async interface.

---

## Common Pitfalls

### Pitfall 1: Staging `core/llm/` Without `__init__.py`
**What goes wrong:** Python cannot import `core.llm.provider` if `core/llm/__init__.py` is not present; tests fail with `ModuleNotFoundError`.
**Why it happens:** `git add core/llm/` stages the directory but only `__init__.py` if explicitly listed; some developers only stage the three main files.
**How to avoid:** Confirm all four files are staged: `__init__.py`, `provider.py`, `schemas.py`, `tools.py`.
**Warning signs:** `ImportError: No module named 'core.llm'` in tests.

### Pitfall 2: Committing `.cursor/` or `CLAUDE.md` with the LLM integration
**What goes wrong:** Unrelated tooling artifacts pollute the integration commit.
**Why it happens:** `git add .` or `git add -A` captures all untracked files.
**How to avoid:** Add files explicitly by path; never use `git add .`.
**Warning signs:** `git status` shows `.cursor/` in "Changes to be committed".

### Pitfall 3: `asyncio_mode="auto"` Requires `pyproject.toml` to Be Committed
**What goes wrong:** If `pyproject.toml` is not staged, CI or a fresh clone will not have `asyncio_mode = "auto"` and all async tests will be collected as plain functions and skipped or error.
**Why it happens:** `pyproject.toml` is currently untracked.
**How to avoid:** Include `pyproject.toml` in the commit.
**Warning signs:** Tests collected but not run; `PytestUnraisableExceptionWarning` for coroutines.

### Pitfall 4: Double-Space in Startup Log vs. ROADMAP Success Criterion
**What goes wrong:** The ROADMAP.md success criterion states the log line as `"LLM provider: extraction=... reply=..."` (single space). The actual `main.py` log uses double space (`"extraction=%s  reply=%s"`).
**Why it happens:** Minor formatting discrepancy introduced during implementation.
**How to avoid:** Either accept the double-space or fix the log format string before committing.
**Warning signs:** When verifying ENV-02 by reading startup logs, the string comparison will fail if testing with exact-match.

### Pitfall 5: `bedroom_count` Extracted but Not Persisted in `LeadProfile`
**What goes wrong:** `_extract_information` returns `bedroom_count` in its dict, but `_create_profile` and `_merge_profile` do not use it. The field is silently dropped.
**Why it happens:** `LeadProfile` dataclass does not have a `bedroom_count` field.
**How to avoid:** This is a known v2 limitation, not a bug. Document it; do not add the field in this phase.
**Warning signs:** None at runtime — this is silent and intentional.

---

## Code Examples

Verified patterns from direct code inspection:

### Constructing the LLM provider at startup
```python
# main.py — verified against git diff HEAD
def _build_llm_provider():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.info("ANTHROPIC_API_KEY not set – running in heuristic-only mode")
        return None
    from core.llm.provider import AnthropicLLMProvider, DEFAULT_MODEL
    extraction_model = os.getenv("ANTHROPIC_MODEL_EXTRACTION") or os.getenv("ANTHROPIC_MODEL") or DEFAULT_MODEL
    reply_model = os.getenv("ANTHROPIC_MODEL_REPLY") or os.getenv("ANTHROPIC_MODEL") or DEFAULT_MODEL
    logger.info("LLM provider: extraction=%s  reply=%s", extraction_model, reply_model)
    return AnthropicLLMProvider(api_key=api_key, extraction_model=extraction_model, reply_model=reply_model)
```

### Mocking the provider for CloserAgent tests
```python
# tests/test_basic.py — verified: 13/13 tests pass
provider = MagicMock()
provider.generate_suggestions = AsyncMock(return_value=[
    SuggestionOutput(message="...", tactics=["value_proposition"], reasoning="..."),
])
closer = CloserAgent(llm_provider=provider)
suggestions = await closer.generate_suggestions(profile=profile, approach="gentle_follow_up", count=3)
provider.generate_suggestions.assert_awaited_once()
```

### Mocking the provider for ListenerAgent tests
```python
# tests/test_basic.py — verified working
provider = MagicMock()
provider.extract_message = AsyncMock(return_value=MessageExtraction(
    budget_min=2_000_000_000, budget_max=3_000_000_000,
    locations=["quận 2"], interest_level="hot", intent="buy",
    property_types=["apartment"], bedroom_count=2,
    key_phrases=["view sông"], open_questions=["Giá có thương lượng không?"],
))
agent = ListenerAgent(lead_store, conv, llm_provider=provider)
result = await agent.process_message(message_text="...", lead_id="lead_001")
provider.extract_message.assert_awaited_once()
```

### Testing fallback on LLM error
```python
# Same for both agents — verified working
provider = MagicMock()
provider.extract_message = AsyncMock(side_effect=RuntimeError("timeout"))
# Agent catches Exception broadly and falls back to heuristics
```

### Git staging the correct files
```bash
# Stage untracked LLM module
git add core/llm/__init__.py core/llm/provider.py core/llm/schemas.py core/llm/tools.py
# Stage pyproject.toml (pytest config)
git add pyproject.toml
# Stage modified files
git add agents/closer.py agents/listener.py main.py requirements.txt tests/test_basic.py .env.example
# Do NOT add: .cursor/ CLAUDE.md core/memory.py integrations/zalo_client.py integrations/zalo_routes.py
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No LLM, heuristic-only extraction | Claude Haiku via tool_use for structured extraction | This phase | More accurate budget/intent/interest extraction from Vietnamese text |
| Template-based reply generation | Claude Haiku generates 3 personalized Vietnamese replies | This phase | Contextual, personalized replies vs. fixed template substitution |
| Sync agent methods | `async` agent methods (`process_message`, `generate_suggestions`) | This implementation | Required for `await llm_provider.*` calls without blocking FastAPI |

**Note on pyproject.toml:** Previously, no `pyproject.toml` existed. It was added with only `[tool.pytest.ini_options] asyncio_mode = "auto"`. This replaces the need for `@pytest.mark.asyncio` decorators on every async test.

---

## Open Questions

1. **`core/memory.py`, `integrations/zalo_client.py`, `integrations/zalo_routes.py` are modified but out of scope**
   - What we know: These files are in `git diff HEAD` but not related to LLM integration
   - What's unclear: Whether their modifications should be committed in this phase or left unstaged
   - Recommendation: Leave them unstaged in this commit to keep the LLM integration commit focused

2. **`CLAUDE.md` is untracked**
   - What we know: It's project documentation, not LLM code
   - What's unclear: Whether it belongs in this commit or a separate one
   - Recommendation: Commit it separately or with the LLM commit — it doesn't affect tests; include if desired

3. **Double-space in startup log format**
   - What we know: `main.py` logs `"extraction=%s  reply=%s"` (double space); ROADMAP success criterion shows single space
   - What's unclear: Whether the verifier will test log output exactly
   - Recommendation: Fix to single space before committing if strict log-string matching is used for ENV-02 verification

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `core/llm/provider.py`, `core/llm/schemas.py`, `core/llm/tools.py`, `agents/listener.py`, `agents/closer.py`, `main.py`, `tests/test_basic.py`
- `python3 -m pytest tests/ -v` — 13 passed, 0 failed (run 2026-03-22)
- `python3 -c "import anthropic; print(anthropic.__version__)"` — 0.86.0 installed
- SDK type inspection: `ToolUseBlock`, `ToolChoiceToolParam`, `RateLimitError`, `InternalServerError` — all present in installed SDK
- `git ls-files --others --exclude-standard` — confirmed untracked files
- `git diff --stat HEAD` — confirmed 9 modified files, 4 untracked LLM files

### Secondary (MEDIUM confidence)
- `pyproject.toml` content — `asyncio_mode = "auto"` confirmed for pytest-asyncio 1.3.0
- `requirements.txt` — `anthropic>=0.40.0` and `pytest-asyncio>=0.23.0` pinned

---

## Metadata

**Confidence breakdown:**
- LLM code correctness: HIGH — all code directly inspected and SDK types verified at runtime
- Test coverage: HIGH — tests run and pass; mock patterns verified correct
- Git staging plan: HIGH — `git ls-files` and `git diff` used to enumerate exact file lists
- ENV config: HIGH — `.env.example` and `main.py` startup logging verified in working tree

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (stable: SDK and pytest-asyncio APIs change slowly)
