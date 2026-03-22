"""
Core data models for Zalo AI Broker Assistant

Defines the fundamental data structures used across all agents:
- Intent: Customer intent classification
- InterestLevel: Lead qualification levels
- LeadProfile: Complete lead information
- Message: Conversation messages
- Suggestion: AI-generated reply suggestions
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict


class Intent(Enum):
    """Customer intent classification"""
    BUY = "buy"
    INVEST = "invest"
    RENT = "rent"
    BROWSE = "browse"


class InterestLevel(Enum):
    """Lead qualification based on urgency and engagement"""
    HOT = "hot"      # Ready to buy, urgent signals
    WARM = "warm"    # Interested, actively researching
    COLD = "cold"    # Just browsing, low engagement


@dataclass
class LeadProfile:
    """Complete lead profile with preferences and interaction history"""
    lead_id: str
    name: Optional[str] = None
    phone: Optional[str] = None
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    locations: List[str] = field(default_factory=list)
    property_types: List[str] = field(default_factory=list)
    intent: Intent = Intent.BROWSE
    interest_level: InterestLevel = InterestLevel.COLD
    last_contact: datetime = field(default_factory=datetime.now)
    total_interactions: int = 0
    response_rate: float = 0.0
    key_phrases: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'lead_id': self.lead_id,
            'name': self.name,
            'phone': self.phone,
            'budget_min': self.budget_min,
            'budget_max': self.budget_max,
            'locations': self.locations,
            'property_types': self.property_types,
            'intent': self.intent.value,
            'interest_level': self.interest_level.value,
            'last_contact': self.last_contact.isoformat(),
            'total_interactions': self.total_interactions,
            'response_rate': self.response_rate,
            'key_phrases': self.key_phrases
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'LeadProfile':
        """Create LeadProfile from dictionary"""
        data['intent'] = Intent(data['intent'])
        data['interest_level'] = InterestLevel(data['interest_level'])
        data['last_contact'] = datetime.fromisoformat(data['last_contact'])
        return cls(**data)


@dataclass
class Message:
    """Conversation message"""
    text: str
    timestamp: datetime
    is_broker: bool
    lead_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'text': self.text,
            'timestamp': self.timestamp.isoformat(),
            'is_broker': self.is_broker,
            'lead_id': self.lead_id
        }


@dataclass
class Suggestion:
    """AI-generated reply suggestion with tactics and confidence"""
    message: str
    tactics: List[str]
    confidence: float
    reasoning: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'message': self.message,
            'tactics': self.tactics,
            'confidence': self.confidence,
            'reasoning': self.reasoning
        }


@dataclass
class FollowUpTask:
    """Scheduled follow-up task"""
    lead_id: str
    scheduled_time: datetime
    priority: str  # "high", "normal", "low"
    action: str    # "quick_reply", "gentle_follow_up", "urgent_follow_up"
    context: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'lead_id': self.lead_id,
            'scheduled_time': self.scheduled_time.isoformat(),
            'priority': self.priority,
            'action': self.action,
            'context': self.context
        }
