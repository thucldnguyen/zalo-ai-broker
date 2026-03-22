# Requirements: Zalo AI Broker

**Defined:** 2026-03-22
**Core Value:** Brokers get instant, personalized Vietnamese reply suggestions powered by Claude Haiku, with heuristic fallback

## v1 Requirements

### LLM Integration

- [ ] **LLM-01**: ListenerAgent uses Claude Haiku to extract budget, location, intent, and interest level from Vietnamese messages when `ANTHROPIC_API_KEY` is set
- [ ] **LLM-02**: CloserAgent uses Claude Haiku to generate 3 personalized Vietnamese reply suggestions when `ANTHROPIC_API_KEY` is set
- [ ] **LLM-03**: Both agents fall back to heuristic/template mode transparently when LLM is unavailable or throws an error
- [ ] **LLM-04**: `core/llm/` (provider, schemas, tools) is committed and tracked in git

### Test Coverage

- [ ] **TEST-01**: ListenerAgent LLM path covered by mocked tests (no real API call required)
- [ ] **TEST-02**: CloserAgent LLM path covered by mocked tests
- [ ] **TEST-03**: All existing tests continue to pass after integration commit

### Environment & Config

- [ ] **ENV-01**: `.env.example` documents `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL_EXTRACTION`, `ANTHROPIC_MODEL_REPLY`
- [ ] **ENV-02**: App logs which mode it starts in (LLM or heuristic-only)

## v2 Requirements

### Observability

- **OBS-01**: LLM call latency and token usage logged per request
- **OBS-02**: Extraction confidence scores surfaced in API response

### Model Flexibility

- **MODEL-01**: Support swapping to claude-sonnet or claude-opus via env var without code changes

## Out of Scope

| Feature | Reason |
|---------|--------|
| PostgreSQL migration | Planned post-MVP; JSON storage is intentional |
| Multi-broker UI | Backend-only in v1 |
| Streaming LLM responses | Not needed for suggestion batches |
| Fine-tuning | Haiku + prompts sufficient for v1 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| LLM-01 | Phase 1 | Pending |
| LLM-02 | Phase 1 | Pending |
| LLM-03 | Phase 1 | Pending |
| LLM-04 | Phase 1 | Pending |
| TEST-01 | Phase 1 | Pending |
| TEST-02 | Phase 1 | Pending |
| TEST-03 | Phase 1 | Pending |
| ENV-01 | Phase 1 | Pending |
| ENV-02 | Phase 1 | Pending |

**Coverage:**
- v1 requirements: 9 total
- Mapped to phases: 9
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-22*
*Last updated: 2026-03-22 after initial definition*
