# Coding Conventions

**Analysis Date:** 2026-03-22

## Naming Patterns

**Files:**
- Snake case for all Python files: `listener.py`, `vietnamese_nlp.py`, `zalo_client.py`
- Group related files in directories: `agents/`, `core/`, `integrations/`, `core/llm/`
- Directories use snake case: `core/llm/`, `data/leads/`, `data/conversations/`

**Functions:**
- Snake case for all function names: `extract_budget()`, `process_message()`, `_hours_since_last_contact()`
- Leading underscore for internal/private methods: `_extract_information()`, `_merge_profile()`, `_calculate_confidence()`
- Async functions named like regular functions, no `async_` prefix: `async def process_message()`, `async def generate_suggestions()`

**Variables:**
- Snake case for variable names: `lead_id`, `budget_min`, `budget_max`, `lead_store`, `conv_history`
- Constant all-caps with underscore: `DEFAULT_MODEL`, `HOT_SIGNALS`, `BUDGET_PATTERNS`, `FOLLOW_UP_INTERVALS`
- Dictionary/mapping variables in all-caps if module-level constants: `TEMPLATES`, `INTENT_KEYWORDS`, `DISTRICTS`, `AREAS`, `PROJECTS`

**Types & Classes:**
- PascalCase for all class names: `LeadProfile`, `ListenerAgent`, `StrategistAgent`, `CloserAgent`, `VietnameseExtractor`, `LeadStore`, `ConversationHistory`, `AnthropicLLMProvider`
- PascalCase for Enum types: `Intent`, `InterestLevel`
- PascalCase for dataclasses: `Message`, `Suggestion`, `FollowUpTask`, `MessageExtraction`, `SuggestionOutput`

## Code Style

**Formatting:**
- Black formatter (version 23.12.0) – no manual configuration file; uses defaults
- Line length: 88 characters (Black default)
- String quotes: Black's default (double quotes when possible)

**Linting:**
- Flake8 (version 6.1.0) – enforces PEP 8 compliance
- No `.flake8` config file in repo; uses defaults

**Indentation:**
- 4 spaces per indentation level (PEP 8 standard)
- No tabs

## Import Organization

**Order:**
1. Standard library imports (`import logging`, `import os`, `import json`)
2. Third-party imports (`import fastapi`, `import anthropic`, `import pydantic`)
3. Local application imports (`from core.models import`, `from agents.listener import`)

**Path Aliases:**
- No path aliases configured
- All imports use absolute paths from project root: `from core.models import LeadProfile`

**Example from `listener.py`:**
```python
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from core.models import LeadProfile, Message, Intent, InterestLevel
from core.vietnamese_nlp import VietnameseExtractor
from core.memory import LeadStore, ConversationHistory
```

## Error Handling

**Patterns:**

1. **Exception Logging + Fallback** (preferred for non-critical operations):
   ```python
   try:
       extraction = await self._llm_provider.extract_message(text, history, response_time_seconds)
       return { "budget_min": extraction.budget_min, ... }
   except Exception as exc:
       logger.warning("LLM extraction failed for lead, falling back to heuristics: %s", exc)
       # Use fallback (heuristics)
   ```
   Used in: `listeners.py:_extract_information()`, `closer.py:generate_suggestions()`

2. **Graceful Degradation with Try/Except/Pass**:
   ```python
   try:
       data = json.loads(line.strip())
       messages.append(Message(**data))
   except:
       continue
   ```
   Used in: `memory.py:ConversationHistory.get_history()` – silently skips malformed JSON lines

3. **Boolean Return for Persistence**:
   ```python
   def save(self, lead: LeadProfile) -> bool:
       try:
           # ... save logic
           return True
       except Exception as e:
           logger.error("Error saving lead %s: %s", lead.lead_id, e)
           return False
   ```
   Used in: `memory.py:LeadStore.save()`, `LeadStore.delete()`

4. **HTTPException for API Errors** (FastAPI):
   ```python
   if not profile:
       raise HTTPException(status_code=404, detail="Lead not found")
   ```
   Used in: `main.py` endpoints

5. **1-Retry with Delay for Transient Errors**:
   ```python
   for attempt in range(2):
       try:
           response = await self._client.messages.create(...)
       except (anthropic.RateLimitError, anthropic.InternalServerError) as exc:
           if attempt == 0:
               logger.warning("Anthropic transient error, retrying: %s", exc)
               await asyncio.sleep(1)
               continue
           raise
   ```
   Used in: `core/llm/provider.py:extract_message()`, `generate_suggestions()`

**When NOT to Catch:**
- Let LLM errors bubble up to agent level; agents decide whether to fall back to heuristics
- Don't catch validation errors; let Pydantic raise ValidationError at API boundary

## Logging

**Framework:** Python's built-in `logging` module

**Patterns:**
- All modules define logger at module level: `logger = logging.getLogger(__name__)`
- Log at module root level: `logger = logging.getLogger(__name__)` captures module name automatically
- Use configured in `main.py`: `logging.basicConfig(level=logging.INFO)`

**Levels:**
- `logger.info()` – major flow events (agent initialization, key decisions)
- `logger.warning()` – recoverable failures (LLM fallback, missing data)
- `logger.error()` – persistent failures (I/O errors, corrupted data)

**Example:**
```python
logger.info("LLM provider: extraction=%s  reply=%s", extraction_model, reply_model)
logger.warning("LLM extraction failed for lead, falling back to heuristics: %s", exc)
logger.error("Error saving lead %s: %s", lead.lead_id, e)
```

## Comments

**When to Comment:**
- Module docstrings (always, at file top): Describe purpose, exports, high-level design
- Class docstrings (always): Describe class purpose and key responsibilities
- Function docstrings (always): Describe args, returns, and purpose
- Complex logic (sparingly): Only if not self-evident from naming
- Design decisions: WHY something is done a certain way (see module docstrings in `agents/`, `core/`)

**Example from `listener.py`:**
```python
"""
Listener Agent - Extract structured information from conversations

Responsibilities:
- Parse incoming Zalo messages
- Extract: budget, locations, intent, interest level
- Update or create lead profiles
- Identify key phrases and preferences

Input: Raw message text
Output: Structured lead data
"""
```

**Format:**
- Module docstrings: Triple quotes at file top, describe purpose + responsibilities
- Class docstrings: Triple quotes after class definition, describe purpose
- Function docstrings: Follow Google-style format (Args, Returns)
- No inline comments (//); prefer self-documenting code with clear naming

## Function Design

**Size:** Functions stay focused; longest is ~30 lines (agent decision logic in `strategist.py`)

**Parameters:**
- Explicit parameters preferred over `**kwargs`
- Type hints required for all parameters: `def extract_budget(self, text: str) -> Tuple[Optional[int], Optional[int]]`
- Default values in function signature: `def process_message(..., is_broker: bool = False, response_time_seconds: Optional[int] = None)`

**Return Values:**
- Type hints on all returns: `-> Dict[str, Any]`, `-> List[Suggestion]`, `-> bool`
- Return meaningful types (dicts for structured data, lists for collections, bool for success/failure)
- Optional returns use `Optional[T]` annotation

**Example from `memory.py`:**
```python
def save(self, lead: LeadProfile) -> bool:
    """
    Save lead profile to disk

    Args:
        lead: LeadProfile to save

    Returns:
        True if successful, False otherwise
    """
```

## Module Design

**Exports:**
- No `__all__` declarations; export by convention (public names at module level)
- Classes are primary export: `ListenerAgent`, `CloserAgent`, `LeadStore`
- Utility functions as secondary: `extract_budget()`, `classify_interest()`

**Barrel Files:**
- No barrel files (`__init__.py`) for re-exports
- Empty `__init__.py` files in all packages for namespace clarity: `agents/__init__.py`, `core/__init__.py`

**Dataclasses:**
- All domain models as dataclasses with `@dataclass`: `LeadProfile`, `Message`, `Suggestion`
- Include `to_dict()` and `from_dict()` methods for JSON serialization
- Use `field(default_factory=...)` for mutable defaults: `locations: List[str] = field(default_factory=list)`

**Example from `models.py`:**
```python
@dataclass
class LeadProfile:
    """Complete lead profile with preferences and interaction history"""
    lead_id: str
    name: Optional[str] = None
    locations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return { 'lead_id': self.lead_id, ... }

    @classmethod
    def from_dict(cls, data: Dict) -> 'LeadProfile':
        """Create LeadProfile from dictionary"""
        return cls(**data)
```

---

*Convention analysis: 2026-03-22*
