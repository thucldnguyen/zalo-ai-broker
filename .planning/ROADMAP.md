# Roadmap: Zalo AI Broker

**Milestone:** v1 — Claude Haiku LLM Integration
**Goal:** Verify, test, and commit the existing Haiku integration so the app runs intelligently in production

---

## Phase 1 — Verify & Ship LLM Integration

**Goal:** All LLM integration code is tested, correct, and committed to git

**Requirements covered:** LLM-01, LLM-02, LLM-03, LLM-04, TEST-01, TEST-02, TEST-03, ENV-01, ENV-02

**Plans:** 2 plans

Plans:
- [ ] 01-01-PLAN.md — Fix log format, verify tests and env config
- [ ] 01-02-PLAN.md — Stage and commit LLM integration files

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
