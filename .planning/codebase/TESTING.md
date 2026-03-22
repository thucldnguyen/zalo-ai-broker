# Testing Patterns

**Analysis Date:** 2026-03-22

## Test Framework

**Runner:**
- pytest 7.4.3
- Config: `pyproject.toml` with asyncio_mode auto-enabled
- pytest-asyncio >= 0.23.0 – enables async test support

**Assertion Library:**
- pytest's built-in assertions (no external library)

**Run Commands:**
```bash
pytest tests/                           # Run all tests
pytest tests/test_basic.py -v           # Verbose output
pytest tests/test_basic.py::TestVietnameseExtractor::test_budget_extraction_range -v  # Single test
pytest --asyncio-mode=auto              # Explicitly enable asyncio mode (default in pyproject.toml)
```

**Pytest Configuration:**
Located in `pyproject.toml`:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

This automatically converts async test methods to pytest fixtures with async support – no manual `@pytest.mark.asyncio` needed on most tests.

## Test File Organization

**Location:**
- Co-located with source code in `tests/` directory
- Single test file: `tests/test_basic.py` covering all modules

**Naming:**
- Test file: `test_basic.py`
- Test classes: `TestVietnameseExtractor`, `TestCloserTemplateFallback`, `TestCloserLLMPath`, `TestListenerLLMPath`
- Test methods: `test_*` convention (e.g., `test_budget_extraction_range`, `test_interest_classification_hot`)

**Structure:**
```
tests/
├── __init__.py        # Empty namespace marker
└── test_basic.py      # All tests (Vietnamese NLP, agents)
```

## Test Structure

**Suite Organization:**
```python
class TestVietnameseExtractor:
    """Test Vietnamese NLP extraction"""

    def setup_method(self):
        """Called before each test method"""
        self.extractor = VietnameseExtractor()

    def test_budget_extraction_range(self):
        """Test budget range extraction"""
        text = "Anh muốn tìm căn tầm 2-3 tỷ"
        min_budget, max_budget = self.extractor.extract_budget(text)

        assert min_budget == 2_000_000_000
        assert max_budget == 3_000_000_000
```

**Patterns:**
- Setup method via `setup_method()` – runs before each test in the class
- No teardown methods (state is temporary/local)
- Each test is independent; fixtures created fresh per test

## Mocking

**Framework:** unittest.mock (Python standard library)

**Patterns:**
```python
from unittest.mock import AsyncMock, MagicMock

def _make_mock_provider(self) -> MagicMock:
    provider = MagicMock()
    provider.generate_suggestions = AsyncMock(
        return_value=[
            SuggestionOutput(
                message="Chào chị Lan!",
                tactics=["value_proposition"],
                reasoning="Warm lead - highlight value match",
            ),
        ]
    )
    return provider

async def test_llm_suggestions_used(self):
    provider = self._make_mock_provider()
    closer = CloserAgent(llm_provider=provider)

    suggestions = await closer.generate_suggestions(...)

    assert len(suggestions) == 3
    provider.generate_suggestions.assert_awaited_once()
```

**What to Mock:**
- LLM providers: Always mock `AnthropicLLMProvider` for unit tests
- External APIs: Mock Zalo client calls (if tested)
- File I/O: Use `tmp_path` fixture for temp directories instead of mocking

**What NOT to Mock:**
- Core models (LeadProfile, Message) – construct real instances
- VietnameseExtractor heuristics – test with real Vietnamese text
- Storage classes (LeadStore, ConversationHistory) – use temp directories

## Fixtures and Factories

**Test Data:**

Helper methods create test objects:
```python
def _make_profile(self) -> LeadProfile:
    return LeadProfile(
        lead_id="test_001",
        name="Anh Minh",
        budget_min=2_000_000_000,
        budget_max=3_000_000_000,
        locations=["quận 2"],
        interest_level=InterestLevel.HOT,
    )
```

Real pytest fixtures for temporary storage:
```python
async def test_llm_extraction_used(self, tmp_path):
    """tmp_path provided by pytest – temporary directory for each test"""
    lead_store = LeadStore(data_dir=str(tmp_path / "leads"))
    conv = ConversationHistory(data_dir=str(tmp_path / "conversations"))
    # Tests have isolated temp directories
```

**Location:**
- Helper methods defined in test classes: `_make_profile()`, `_make_mock_provider()`
- Pytest fixtures used inline: `tmp_path` for temporary file systems
- No separate fixtures module; everything in `tests/test_basic.py`

## Coverage

**Requirements:** Not enforced

**View Coverage:**
No coverage command in requirements; to add:
```bash
pip install pytest-cov
pytest --cov=. --cov-report=html
```

## Test Types

**Unit Tests (Dominant):**
- Test individual functions/methods in isolation
- Mock external dependencies (LLM, file I/O if needed)
- Examples:
  - `TestVietnameseExtractor.test_budget_extraction_range()` – pure function, no mocks
  - `TestCloserTemplateFallback.test_closer_generates_suggestions()` – CloserAgent without LLM

**Integration Tests:**
- Test agent methods with mocked LLM but real storage
- Example:
  ```python
  async def test_llm_extraction_used(self, tmp_path):
      """Tests ListenerAgent + LeadStore + ConversationHistory"""
      lead_store = LeadStore(data_dir=str(tmp_path / "leads"))
      conv = ConversationHistory(data_dir=str(tmp_path / "conversations"))
      agent = ListenerAgent(lead_store, conv, llm_provider=provider)
      result = await agent.process_message(...)
      # Verifies full agent flow with real storage
  ```

**E2E Tests:**
- Not present
- Would require running full FastAPI server (`main.py` endpoints)
- Manual testing via `example_usage.py` demonstrates API flow

## Common Patterns

**Async Testing:**
```python
async def test_llm_suggestions_used(self):
    """Async test – pytest-asyncio auto-detects and runs with async loop"""
    provider = self._make_mock_provider()
    closer = CloserAgent(llm_provider=provider)

    suggestions = await closer.generate_suggestions(
        profile=self._make_profile(),
        approach="gentle_follow_up",
        count=3,
    )

    assert len(suggestions) == 3
    provider.generate_suggestions.assert_awaited_once()
```

Notes:
- No `@pytest.mark.asyncio` needed (asyncio_mode="auto" in config)
- `assert_awaited_once()` verifies async mock was awaited

**Error Testing:**
```python
async def test_llm_failure_falls_back_to_templates(self):
    """Verifies fallback behavior on LLM error"""
    provider = MagicMock()
    provider.generate_suggestions = AsyncMock(side_effect=RuntimeError("API down"))
    closer = CloserAgent(llm_provider=provider)

    suggestions = await closer.generate_suggestions(
        profile=self._make_profile(),
        approach="soft_touch",
        count=2,
    )

    # Should still get suggestions (from templates)
    assert len(suggestions) == 2
    assert all(s.confidence > 0 for s in suggestions)
```

Pattern: Test exception path explicitly; verify fallback behavior works

**Testing Deterministic Fallback:**
```python
async def test_closer_no_fabricated_numbers_in_templates(self):
    """Template fallback must not contain random integers for count/percent."""
    closer = CloserAgent()
    profile = self._make_profile()
    suggestions = await closer.generate_suggestions(...)

    for s in suggestions:
        # Assert old placeholder patterns are gone
        assert "{count}" not in s.message
        assert "{percent}" not in s.message
```

Pattern: Verify templates are rendered without leftover placeholders

## Test Coverage Summary

**Well-Tested:**
- `VietnameseExtractor` – all extraction methods (budget, locations, intent, interest level)
- `CloserAgent` – template fallback AND LLM path
- `ListenerAgent` – LLM path with mock provider AND fallback heuristics

**Gaps:**
- No tests for `StrategistAgent` (decision logic untested)
- No tests for FastAPI endpoints in `main.py`
- No tests for `ZaloClient`, `ZaloRoutes` (Zalo integration)
- No tests for `LeadStore`/`ConversationHistory` persistence
- No mocking of actual file I/O; temp directories work but no explicit storage tests

## Running Tests

**Full suite:**
```bash
pytest tests/test_basic.py -v
```

**Single test class:**
```bash
pytest tests/test_basic.py::TestVietnameseExtractor -v
```

**Single test:**
```bash
pytest tests/test_basic.py::TestVietnameseExtractor::test_budget_extraction_range -v
```

**Watch mode** (requires pytest-watch):
```bash
pip install pytest-watch
ptw tests/
```

---

*Testing analysis: 2026-03-22*
