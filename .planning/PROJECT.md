# Zalo AI Broker

## What This Is

A FastAPI backend that helps Vietnamese real estate brokers close deals faster. It processes customer messages in Vietnamese through a three-agent pipeline (Listener → Strategist → Closer), qualifies leads, and generates personalized Vietnamese reply suggestions. Deployed on Railway and integrated with Zalo Official Account webhooks.

## Core Value

Brokers get instant, personalized Vietnamese reply suggestions for every customer message — powered by Claude Haiku when available, heuristic fallback otherwise.

## Requirements

### Validated

- ✓ Rule-based Vietnamese NLP extraction (budget, location, intent, interest level) — existing
- ✓ Three-agent pipeline (Listener → Strategist → Closer) — existing
- ✓ JSON-based lead storage and conversation history — existing
- ✓ Zalo webhook integration (send/receive messages, OAuth token management) — existing
- ✓ Template-based Vietnamese reply generation with persuasion tactics — existing
- ✓ FastAPI REST API (hot leads, follow-up scheduling, lead profiles) — existing

### Active

- [ ] Claude Haiku integration verified working end-to-end (extraction + reply generation)
- [ ] All tests pass with mocked LLM calls
- [ ] `core/llm/` code committed to git alongside modified agents and main.py

### Out of Scope

- PostgreSQL migration — planned for post-MVP, JSON storage is intentional for now
- Multi-broker UI dashboard — backend-only in v1
- New LLM capabilities beyond extraction and reply generation — extend after current integration is stable

## Context

The LLM integration (`core/llm/provider.py`, `core/llm/schemas.py`, `core/llm/tools.py`) was implemented and wired into both `ListenerAgent` and `CloserAgent` with heuristic fallback. The code is untracked (not yet committed). The integration activates when `ANTHROPIC_API_KEY` is set in `.env`; without it, heuristic extraction and template replies are used transparently.

Default model: `claude-haiku-4-5-20251001` for both extraction and reply generation. Override via `ANTHROPIC_MODEL_EXTRACTION` / `ANTHROPIC_MODEL_REPLY` env vars.

## Constraints

- **Tech stack**: Python 3.11, FastAPI, `anthropic>=0.40.0` — no new dependencies
- **Compatibility**: Heuristic fallback must remain intact — LLM is an enhancement, not a hard requirement
- **Deployment**: Railway — env vars managed via Railway dashboard, not committed to git

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Claude Haiku as default LLM | Cost-efficient for high-volume message processing | — Pending |
| Heuristic fallback for all LLM calls | Resilience — app must work without API key | ✓ Good |
| Anthropic tool_use for structured output | Guarantees schema-valid extraction and reply JSON | — Pending |

---

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-22 after initialization*
