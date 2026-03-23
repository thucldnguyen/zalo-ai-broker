"""
Basic tests for Zalo AI Broker Assistant

Run with: pytest tests/
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from core.models import Intent, InterestLevel, LeadProfile
from core.vietnamese_nlp import VietnameseExtractor
from core.memory import LeadStore
from core.llm.schemas import MessageExtraction, SuggestionOutput
from agents.listener import ListenerAgent
from agents.strategist import StrategistAgent
from agents.closer import CloserAgent


# ---------------------------------------------------------------------------
# Vietnamese NLP (heuristic) – synchronous, no LLM needed
# ---------------------------------------------------------------------------

class TestVietnameseExtractor:
    """Test Vietnamese NLP extraction"""

    def setup_method(self):
        self.extractor = VietnameseExtractor()

    def test_budget_extraction_range(self):
        """Test budget range extraction"""
        text = "Anh muốn tìm căn tầm 2-3 tỷ"
        min_budget, max_budget = self.extractor.extract_budget(text)

        assert min_budget == 2_000_000_000
        assert max_budget == 3_000_000_000

    def test_budget_extraction_single(self):
        """Test single budget value (creates ±15% range)"""
        text = "Budget khoảng 2 tỷ"
        min_budget, max_budget = self.extractor.extract_budget(text)

        assert min_budget == 1_700_000_000  # 2B * 0.85
        assert max_budget == 2_300_000_000  # 2B * 1.15

    def test_location_extraction(self):
        """Test location extraction"""
        text = "Tìm căn ở Quận 2 hoặc Thảo Điền"
        locations = self.extractor.extract_locations(text)

        assert "quận 2" in locations
        assert "thảo điền" in locations

    def test_interest_classification_hot(self):
        """Test hot lead classification"""
        text = "Cần gấp, trong tuần này"
        interest = self.extractor.classify_interest(text)

        assert interest == InterestLevel.HOT

    def test_interest_classification_warm(self):
        """Test warm lead classification"""
        text = "Đang tìm hiểu, muốn xem thông tin"
        interest = self.extractor.classify_interest(text)

        assert interest == InterestLevel.WARM

    def test_intent_detection_buy(self):
        """Test buy intent detection"""
        text = "Anh muốn mua để về ở"
        intent = self.extractor.detect_intent(text)

        assert intent == Intent.BUY

    def test_intent_detection_invest(self):
        """Test invest intent detection"""
        text = "Tìm căn để đầu tư cho thuê"
        intent = self.extractor.detect_intent(text)

        assert intent == Intent.INVEST


# ---------------------------------------------------------------------------
# Closer: template fallback (no LLM provider)
# ---------------------------------------------------------------------------

class TestCloserTemplateFallback:
    """CloserAgent without LLM uses template fallback"""

    def _make_profile(self) -> LeadProfile:
        return LeadProfile(
            lead_id="test_001",
            name="Anh Minh",
            budget_min=2_000_000_000,
            budget_max=3_000_000_000,
            locations=["quận 2"],
            interest_level=InterestLevel.HOT,
        )

    async def test_closer_generates_suggestions(self):
        """Closer without LLM generates suggestions via templates"""
        closer = CloserAgent()  # no llm_provider
        profile = self._make_profile()

        suggestions = await closer.generate_suggestions(
            profile=profile,
            approach="urgent_follow_up",
            count=2,
        )

        assert len(suggestions) == 2
        assert all(s.confidence > 0 for s in suggestions)
        assert all(len(s.tactics) > 0 for s in suggestions)

    async def test_closer_no_fabricated_numbers_in_templates(self):
        """Template fallback must not contain random integers for count/percent."""
        closer = CloserAgent()
        profile = self._make_profile()
        suggestions = await closer.generate_suggestions(
            profile=profile,
            approach="social_proof",
            count=3,
        )
        for s in suggestions:
            # The old templates had {count} and {percent} placeholders backed by
            # random.randint – assert those raw placeholders are gone.
            assert "{count}" not in s.message
            assert "{percent}" not in s.message


# ---------------------------------------------------------------------------
# Closer: LLM path (mocked provider)
# ---------------------------------------------------------------------------

class TestCloserLLMPath:
    """CloserAgent with a mocked LLMProvider uses LLM output."""

    def _make_profile(self) -> LeadProfile:
        return LeadProfile(
            lead_id="test_002",
            name="Chị Lan",
            budget_min=3_000_000_000,
            budget_max=5_000_000_000,
            locations=["bình thạnh"],
            interest_level=InterestLevel.WARM,
        )

    def _make_mock_provider(self) -> MagicMock:
        provider = MagicMock()
        provider.generate_suggestions = AsyncMock(
            return_value=[
                SuggestionOutput(
                    message="Chào chị Lan! Em có căn hộ view sông phù hợp với ngân sách của chị ạ.",
                    tactics=["value_proposition"],
                    reasoning="Warm lead - highlight value match",
                ),
                SuggestionOutput(
                    message="Chị Lan ơi, căn hộ ở Bình Thạnh chị đang tìm, em vừa cập nhật danh sách mới nhất ạ.",
                    tactics=["soft_touch"],
                    reasoning="Gentle re-engagement",
                ),
                SuggestionOutput(
                    message="Khu Bình Thạnh chị quan tâm có nhiều lựa chọn tốt trong tầm giá chị ạ.",
                    tactics=["social_proof"],
                    reasoning="Build trust",
                ),
            ]
        )
        return provider

    async def test_llm_suggestions_used(self):
        """When LLM provider is present, its output is returned."""
        provider = self._make_mock_provider()
        closer = CloserAgent(llm_provider=provider)

        suggestions = await closer.generate_suggestions(
            profile=self._make_profile(),
            approach="gentle_follow_up",
            count=3,
        )

        assert len(suggestions) == 3
        assert suggestions[0].message.startswith("Chào chị Lan")
        provider.generate_suggestions.assert_awaited_once()

    async def test_llm_failure_falls_back_to_templates(self):
        """If LLM raises, templates are used instead."""
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


# ---------------------------------------------------------------------------
# Listener: LLM path (mocked provider)
# ---------------------------------------------------------------------------

class TestListenerLLMPath:
    """ListenerAgent with a mocked LLMProvider."""

    def _make_mock_provider(self, extraction: MessageExtraction) -> MagicMock:
        provider = MagicMock()
        provider.extract_message = AsyncMock(return_value=extraction)
        return provider

    async def test_llm_extraction_used(self, tmp_path):
        """Listener calls LLM provider and builds profile from result."""
        extraction = MessageExtraction(
            budget_min=2_000_000_000,
            budget_max=3_000_000_000,
            locations=["quận 2", "thảo điền"],
            interest_level="hot",
            intent="buy",
            property_types=["apartment"],
            bedroom_count=2,
            key_phrases=["view sông"],
            open_questions=["Giá có thương lượng không?"],
        )
        provider = self._make_mock_provider(extraction)

        lead_store = LeadStore(data_dir=str(tmp_path / "leads"))
        from core.memory import ConversationHistory
        conv = ConversationHistory(data_dir=str(tmp_path / "conversations"))
        agent = ListenerAgent(lead_store, conv, llm_provider=provider)

        result = await agent.process_message(
            message_text="Em muốn mua căn hộ 2PN ở Quận 2, tầm 2-3 tỷ, cần gấp",
            lead_id="lead_llm_01",
        )

        assert result["is_new_lead"] is True
        profile = result["profile"]
        assert profile.budget_min == 2_000_000_000
        assert profile.interest_level == InterestLevel.HOT
        assert profile.intent == Intent.BUY
        assert "quận 2" in profile.locations
        provider.extract_message.assert_awaited_once()

    async def test_llm_failure_falls_back_to_heuristics(self, tmp_path):
        """If LLM raises, heuristics fill in the extraction."""
        provider = MagicMock()
        provider.extract_message = AsyncMock(side_effect=RuntimeError("timeout"))

        lead_store = LeadStore(data_dir=str(tmp_path / "leads"))
        from core.memory import ConversationHistory
        conv = ConversationHistory(data_dir=str(tmp_path / "conversations"))
        agent = ListenerAgent(lead_store, conv, llm_provider=provider)

        result = await agent.process_message(
            message_text="Tìm căn hộ ở Quận 2 tầm 2-3 tỷ",
            lead_id="lead_fallback_01",
        )

        # Heuristics should still extract something
        profile = result["profile"]
        assert profile.budget_min == 2_000_000_000
        assert "quận 2" in profile.locations


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
