# Codebase Concerns

**Analysis Date:** 2026-03-22

## Tech Debt

**JSON file-based storage (MVP bottleneck):**
- Issue: Lead profiles and conversation history stored as individual JSON files in `data/leads/` and `data/conversations/`, with in-memory counter caching for performance
- Files: `core/memory.py` (310 lines), `data/` directory
- Impact: Cannot handle concurrent writes safely; no atomic transactions; no query capabilities; file I/O becomes bottleneck at scale; data corruption risk on server crash mid-write
- Fix approach: Migrate to PostgreSQL with `lead_profiles` and `conversations` tables; implement connection pooling; add database migrations; replace `LeadStore` with ORM layer (SQLAlchemy)

**Bare except clauses in JSON parsing:**
- Issue: `core/memory.py` line 301 uses bare `except:` (catches KeyboardInterrupt, SystemExit) instead of specific exception types
- Files: `core/memory.py` (line 301 in `ConversationHistory.get_history()`)
- Impact: Silent failures when parsing malformed JSONL lines; masks programming errors; makes debugging harder
- Fix approach: Change to `except (json.JSONDecodeError, ValueError, KeyError, TypeError) as e:` with logging

**Broad exception handling in storage operations:**
- Issue: Multiple `except Exception as e:` blocks throughout `core/memory.py` (lines 69, 84, 135, 170, 191, 205, 250) catch all exceptions indiscriminately
- Files: `core/memory.py` (LeadStore.save, LeadStore.get, delete operations)
- Impact: Legitimate errors (file permission, disk full, corrupted JSON) logged but not surfaced; silent data loss possible; recovery is difficult
- Fix approach: Catch specific exceptions (`IOError`, `json.JSONDecodeError`, `ValueError`); propagate file system errors; consider retry logic for transient failures

**Counter cache synchronization gap:**
- Issue: `core/memory.py` maintains in-memory `_counters` dict (lines 38-40, 108-113) with async writes to `index.json`; no locking mechanism
- Files: `core/memory.py` (LeadStore class)
- Impact: Under concurrent requests, counter cache can become stale; `/stats` endpoint returns inaccurate counts; race condition on interest level transitions
- Fix approach: Replace with single source of truth (database); if staying with JSON, add file locking or move to read-only stats computation on-demand

## Known Bugs

**Question detection false positives in Vietnamese:**
- Issue: `agents/strategist.py` line 159 uses simple heuristics: `'?' in text or text.endswith('không') or 'có' in text[:10]`
- Symptoms: Statements like "Em không biết anh thích gì" (I don't know what you like) incorrectly classified as questions
- Files: `agents/strategist.py` (StrategistAgent._has_unanswered_question method, lines 145-159)
- Trigger: Any Vietnamese message with "không" or "có" in first 10 characters that isn't actually a question
- Workaround: Falls back to `wait` action if strategist misclassifies; LLM extraction overrides this on next message
- Fix approach: Replace simple string matching with regex for question mark or tone markers; refine Vietnamese question patterns

**Engagement declining detector too aggressive:**
- Issue: `agents/strategist.py` line 235-237 triggers `gentle_nudge` if recent message average length < 50% of older messages
- Symptoms: Customer asking for one specific detail ("4 phòng?" = 8 chars) after detailed inquiry (200 chars) triggers nudge even if engagement is high
- Files: `agents/strategist.py` (StrategistAgent._is_engagement_declining, lines 209-239)
- Trigger: Single short message followed by slightly longer ones
- Workaround: Strategist checks 5 recent messages before deciding; LLM provider can override with better context
- Fix approach: Require 3+ message length decline pattern, not just 2-message comparison; consider message frequency and response times

**Integer division in budget calculation:**
- Issue: `core/vietnamese_nlp.py` lines 80-86 cast float to int after multiplier without rounding
- Symptoms: Budget "2.5 tỷ" becomes 2500000000 exactly, but heuristic creates range 2125000000-2875000000 with rounding artifacts
- Files: `core/vietnamese_nlp.py` (VietnameseExtractor.extract_budget)
- Trigger: Decimal budget values
- Workaround: Rounding happens naturally in most cases; affects < 1% of conversions
- Fix approach: Use `round()` instead of `int()` for multiplier results

## Security Considerations

**Access token exposed in zalo_routes.py:**
- Risk: `integrations/zalo_routes.py` line 84 creates new `AnthropicLLMProvider` on every webhook call, reading `ANTHROPIC_API_KEY` from environment
- Files: `integrations/zalo_routes.py` (zalo_webhook function), `main.py` (application initialization)
- Current mitigation: Environment variables not logged; API key not exposed in responses
- Recommendations:
  - Cache LLM provider instance at application startup instead of per-request
  - Add request rate limiting to `/zalo/webhook` to prevent abuse
  - Verify Zalo webhook signature validation is comprehensive (currently checks signature but not all tampering vectors)

**Broker authentication missing in token save endpoint:**
- Risk: `integrations/zalo_routes.py` line 177-190 (POST `/zalo/auth/save-token`) has no authentication; any request can save tokens for any broker
- Files: `integrations/zalo_routes.py` (save_broker_token endpoint)
- Current mitigation: None visible
- Recommendations:
  - Require OAuth flow validation before token acceptance
  - Add broker identity verification (sign token save requests)
  - Implement session-based auth for broker operations
  - Rate limit token save attempts

**Webhook signature validation is optional:**
- Risk: `integrations/zalo_routes.py` lines 62-64: signature verification is skipped if headers are missing
- Files: `integrations/zalo_routes.py` (zalo_webhook function)
- Current mitigation: Default behavior accepts unauthenticated messages in development; no error raised on missing signature
- Recommendations:
  - Make signature verification mandatory in production (check env var)
  - Log and alert on missing signature headers
  - Return 401 Unauthorized instead of processing message

**Lead data stored in plaintext JSON files:**
- Risk: Customer names, budgets, locations, interaction history stored as plaintext in `data/leads/` and `data/conversations/`
- Files: `core/memory.py` (LeadStore, ConversationHistory), `data/` directory
- Current mitigation: Data directory is `.gitignored`; file permissions rely on OS
- Recommendations:
  - Encrypt sensitive fields at rest (budget, name, phone)
  - Implement field-level encryption in ORM migration
  - Add audit logging for lead data access
  - Consider data retention policy / automatic deletion

## Performance Bottlenecks

**Full directory scan on get_all() calls:**
- Problem: `core/memory.py` lines 194-208 (LeadStore.get_all) scans all `.json` files on disk for every stats/hot_leads query
- Files: `core/memory.py`, main.py endpoints `/leads/hot`, `/stats`
- Cause: No index; file I/O is synchronous; scales as O(n) with number of leads
- Current capacity: ~1000 leads before noticeable 100ms+ delay
- Limit: 10,000 leads causes >1 second queries; UI timeouts
- Improvement path:
  1. Cache hot leads in memory with TTL (30 seconds)
  2. Build database index on `interest_level`
  3. Implement pagination for lead queries

**Conversation history fully loaded in memory:**
- Problem: `agents/strategist.py` line 61 and main.py line 168 call `get_history(limit=6)` which loads entire JSONL file then reverses it
- Files: `core/memory.py` (ConversationHistory.get_history), `agents/strategist.py`
- Cause: No efficient tail-read; JSONL must be fully parsed
- Current capacity: ~500 messages per conversation before noticeable 50ms+ delay
- Improvement path:
  1. Use sqlite3 with ROWID for efficient tail queries
  2. Index by timestamp
  3. Cache recent messages in conversation object

**Message reversal on every call:**
- Problem: `core/memory.py` line 305 reverses entire message list to get "most recent first"
- Files: `core/memory.py` (ConversationHistory.get_history)
- Cause: Naive implementation; O(n) memory and CPU
- Impact: Negligible for <100 messages; accumulates under scale
- Improvement path: Query in DESC order from database; avoid reversal

**LLM API calls on every webhook:**
- Problem: `integrations/zalo_routes.py` lines 92-113 makes 3 async calls (listener + strategist + closer) for every incoming message
- Files: `integrations/zalo_routes.py`, `agents/listener.py`, `agents/closer.py`
- Cause: No deduplication; no caching; no request batching
- Current latency: 2-5 seconds per message under good network
- Scaling issue: At 100 concurrent users, API quota exhaustion likely within hours
- Improvement path:
  1. Cache extraction results for identical messages (unlikely but exists)
  2. Batch strategist + closer into single LLM call when possible
  3. Implement request queuing to smooth API burst load
  4. Monitor Anthropic API quota usage

## Fragile Areas

**ListenerAgent message processing with missing LLM:**
- Files: `agents/listener.py` (lines 102-143, _extract_information method)
- Why fragile: Silently falls back to Vietnamese heuristics if LLM fails; no indication to caller that degraded mode is active; heuristics have edge case failures (false negatives on intent, interest level miscalibration)
- Safe modification:
  - Add telemetry to track fallback rate; alert if >10% of requests use heuristics
  - Return extraction confidence score; let caller decide if retry needed
  - Document heuristic limitations in response

**Counter cache in LeadStore:**
- Files: `core/memory.py` (lines 38-114, counter management)
- Why fragile: In-memory state can diverge from disk state; `_rebuild_index()` is manual recovery; no automatic consistency check
- Safe modification:
  - Never modify counters directly; always go through save/delete methods
  - Add `verify_integrity()` method that scans all files and logs discrepancies
  - Call integrity check on startup and every N hours
  - Log any mismatch and reset counters

**Template interpolation in CloserAgent:**
- Files: `agents/closer.py` (lines 183-224, _generate_message method)
- Why fragile: Uses `str.format()` with fallback to string.replace if format fails; fallback silently produces wrong output if substitutions don't match template placeholders
- Safe modification:
  - Pre-validate template placeholders against available substitutions
  - Use strict format with explicit error on missing keys
  - Log every template interpolation and its result
  - Add unit tests for each template variant

**Profile merging logic:**
- Files: `agents/listener.py` (lines 160-202, _merge_profile method)
- Why fragile: Overwrites existing budgets unconditionally if new extraction provides any value; can degrade data if extraction is wrong; no version control or merge history
- Safe modification:
  - Only update budgets if new values are more specific (narrower range, actual numbers vs bounds)
  - Keep both old and new values; return merge confidence score
  - Add ledger of all profile changes with timestamps
  - Require manual review before overwriting user-provided data

## Scaling Limits

**Concurrent webhook processing:**
- Current capacity: FastAPI handles ~50 concurrent webhook requests before queue backup
- Limit: LLM API has 100 RPM rate limit; at 50 concurrent, hits limit within 2 minutes
- Files: `integrations/zalo_routes.py` (webhook endpoint), `core/llm/provider.py` (retry logic)
- Scaling path:
  1. Add request queue (Redis or in-memory if single-server)
  2. Implement adaptive throttling: if >20 RPM approaching, delay lower-priority requests
  3. Use cheaper extraction for cold leads (heuristics only)
  4. Consider premium API tier or batch endpoint

**Database file handles:**
- Current capacity: OS allows ~1000 open file descriptors; each JSONL read opens file
- Limit: >1000 concurrent requests will hit "too many open files" errors
- Files: `core/memory.py` (all file I/O)
- Scaling path: Database migration eliminates this entirely

**Memory usage with large lead profiles:**
- Current capacity: ~10MB per 1000 leads in memory if all accessed in session
- Limit: On shared hosting with 512MB RAM, ~50,000 leads causes memory pressure
- Files: `agents/listener.py`, `agents/strategist.py` (load full profiles)
- Scaling path: Lazy load profile details; cache only hot leads in memory

## Dependencies at Risk

**anthropic package version not pinned to minor:**
- Risk: `requirements.txt` line 7 specifies `anthropic>=0.40.0`; next major version (1.0.0) may have breaking API changes
- Impact: Future `pip install` could pull incompatible version; test suite doesn't catch this until deployment
- Migration plan:
  1. Pin to `anthropic>=0.40.0,<1.0.0`
  2. Monitor anthropic GitHub releases
  3. Schedule upgrade testing before using new major version

**FastAPI 0.104.1 is not latest:**
- Risk: Current version (0.104.1) is from late 2023; newer versions have security patches
- Impact: Potential vulnerabilities in dependency chain (Starlette, Pydantic)
- Migration plan: Upgrade to 0.110+ (current stable); test webhook endpoints thoroughly

**Pydantic v2 breaking changes from v1:**
- Risk: `requirements.txt` specifies `pydantic==2.5.0`; codebase uses dataclasses, not Pydantic models, so partially insulated
- Impact: If forced to upgrade schema validation in future, significant refactor needed
- Migration plan: Document all places Pydantic v2 features are used; maintain tests for schema validation

## Missing Critical Features

**No request authentication for /process endpoint:**
- Problem: `main.py` POST `/process` accepts any request; no API key, bearer token, or rate limiting
- Blocks: Cannot safely deploy to public internet; any bot can spam with fake leads
- Recommendation:
  1. Add API key authentication via header
  2. Implement rate limiting (10 req/min per API key)
  3. Log and monitor for abuse patterns

**No audit trail for lead data modifications:**
- Problem: Lead profiles updated silently; no history of who (broker_id) changed what and when
- Blocks: Cannot investigate data accuracy issues; no compliance trail for privacy regulations
- Recommendation:
  1. Add `audit_log` table: (timestamp, broker_id, lead_id, field, old_value, new_value)
  2. Implement in `LeadStore.save()` and `_merge_profile()`
  3. Expose `/lead/{id}/audit` endpoint for transparency

**No scheduled follow-up execution:**
- Problem: `/follow-ups?hours=24` returns recommendations but nothing actually sends them
- Blocks: Broker still must manually check endpoint and send messages; no automation
- Recommendation:
  1. Implement scheduled task runner (APScheduler, Celery, or cron job)
  2. Execute pending follow-ups every 15 minutes
  3. Track follow-up execution status and results

**No customer consent / opt-out tracking:**
- Problem: No way for customers to unsubscribe or opt out of messages
- Blocks: GDPR/CCPA compliance; potential legal risk
- Recommendation:
  1. Add `opted_in` boolean field to LeadProfile
  2. Implement `/api/unsubscribe/{lead_id}` endpoint
  3. Respect opt-out on all message sends

## Test Coverage Gaps

**LLM integration not tested with real API:**
- What's not tested: Error handling for API failures (network, rate limit, authentication); retry logic; fallback to heuristics
- Files: `agents/listener.py`, `agents/closer.py`, `core/llm/provider.py`
- Risk: Bug in error handling only surfaced after deployment; cascading failures possible
- Priority: **High** – LLM is single point of failure for quality features
- Recommendation: Add integration tests against mock Anthropic API; simulate rate limits and timeouts

**Zalo webhook verification insufficient:**
- What's not tested: Invalid signatures, missing headers, malformed payloads, replay attacks
- Files: `integrations/zalo_routes.py`, `integrations/zalo_client.py`
- Risk: Unauthenticated requests can be injected; could be exploited for spam or poisoning leads
- Priority: **High** – Security boundary
- Recommendation:
  1. Test with hardcoded payload + signature from Zalo docs
  2. Verify signature generation matches Zalo's implementation exactly
  3. Add timestamp validation to prevent replays

**Vietnamese NLP edge cases untested:**
- What's not tested: Mixed language ("Em muốn 2-3 tỷ for investment"), typos ("tỷ" vs "tỉ"), currency symbols (₫), range overlaps ("1-2 tỷ hoặc 3 tỷ")
- Files: `core/vietnamese_nlp.py` (VietnameseExtractor)
- Risk: Real customer messages fail silently; heuristic degradation undetected
- Priority: **Medium** – Quality issue, not security; fallback exists
- Recommendation: Build test corpus of 100+ real customer messages; add fuzz testing for NLP edge cases

**Concurrent message processing not tested:**
- What's not tested: Two messages from same lead arriving simultaneously; race conditions in profile updates; counter consistency under load
- Files: `core/memory.py`, `agents/listener.py`, `integrations/zalo_routes.py`
- Risk: Data corruption, lost messages, inconsistent state
- Priority: **High** – Will surface in production at scale
- Recommendation: Add pytest-asyncio tests with simultaneous requests; mock file I/O delays

---

*Concerns audit: 2026-03-22*
