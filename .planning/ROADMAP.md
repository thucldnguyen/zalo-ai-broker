# Roadmap: Zalo AI Broker

**Milestone:** v1 — Claude Haiku LLM Integration
**Goal:** Verify, test, and commit the existing Haiku integration so the app runs intelligently in production

---

## Phase 1 — Verify & Ship LLM Integration

**Goal:** All LLM integration code is tested, correct, and committed to git

**Requirements covered:** LLM-01, LLM-02, LLM-03, LLM-04, TEST-01, TEST-02, TEST-03, ENV-01, ENV-02

### Plans

1. **Audit LLM code** — Review `core/llm/` for correctness: provider retry logic, tool schemas, message builders, schema validation
2. **Test LLM paths** — Write/fix mocked tests for ListenerAgent and CloserAgent LLM paths; ensure all tests pass
3. **Verify env config** — Confirm `.env.example` documents all LLM vars; verify startup logging shows correct mode
4. **Commit & integrate** — Stage and commit `core/llm/`, modified agents, main.py; verify clean git state

**Success criteria:**
- `pytest tests/ -v` passes 100%
- `core/llm/` directory committed to git
- App starts and logs "LLM provider: extraction=claude-haiku-4-5-20251001 reply=claude-haiku-4-5-20251001" when key is set
- App starts and logs "heuristic-only mode" when key is absent

---

## Backlog (v2+)

- LLM call observability (latency, token usage per request)
- Extraction confidence scores in API response
- Model swap via env var (sonnet/opus)

---
*Roadmap created: 2026-03-22*
