"""
Basic tests for Zalo AI Broker Assistant

Run with: pytest tests/
"""

import pytest
from datetime import datetime

from core.models import Intent, InterestLevel, LeadProfile
from core.vietnamese_nlp import VietnameseExtractor
from core.memory import LeadStore
from agents.listener import ListenerAgent
from agents.strategist import StrategistAgent
from agents.closer import CloserAgent


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
        
        assert 'quận 2' in locations
        assert 'thảo điền' in locations
    
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


class TestAgents:
    """Test agent functionality"""
    
    def test_listener_creates_profile(self):
        """Test Listener creates new lead profile"""
        # This test would require temporary storage
        # Skipping for MVP - would implement with fixtures
        pass
    
    def test_strategist_follow_up_timing(self):
        """Test Strategist follow-up timing rules"""
        # Would test hot (2h), warm (24h), cold (72h) rules
        pass
    
    def test_closer_generates_suggestions(self):
        """Test Closer generates Vietnamese messages"""
        closer = CloserAgent()
        
        # Create test profile
        profile = LeadProfile(
            lead_id="test_001",
            name="Anh Minh",
            budget_min=2_000_000_000,
            budget_max=3_000_000_000,
            locations=["quận 2"],
            interest_level=InterestLevel.HOT
        )
        
        suggestions = closer.generate_suggestions(
            profile=profile,
            approach="urgent_follow_up",
            count=2
        )
        
        assert len(suggestions) == 2
        assert all(s.confidence > 0 for s in suggestions)
        assert all(len(s.tactics) > 0 for s in suggestions)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
