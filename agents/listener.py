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

from datetime import datetime
from typing import Optional, Dict, Any

from core.models import LeadProfile, Message, Intent, InterestLevel
from core.vietnamese_nlp import VietnameseExtractor
from core.memory import LeadStore, ConversationHistory


class ListenerAgent:
    """
    Agent that listens to conversations and extracts structured data
    """
    
    def __init__(self, lead_store: LeadStore, conversation_history: ConversationHistory):
        """
        Initialize Listener Agent
        
        Args:
            lead_store: Storage for lead profiles
            conversation_history: Storage for conversation messages
        """
        self.extractor = VietnameseExtractor()
        self.lead_store = lead_store
        self.conv_history = conversation_history
    
    def process_message(
        self,
        message_text: str,
        lead_id: str,
        is_broker: bool = False,
        response_time_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Process an incoming message and update lead profile
        
        Args:
            message_text: The message text
            lead_id: Unique identifier for the lead
            is_broker: True if message is from broker, False if from customer
            response_time_seconds: Time customer took to respond (for interest scoring)
        
        Returns:
            Dictionary with extracted data and updated profile
        """
        # Save message to conversation history
        message = Message(
            text=message_text,
            timestamp=datetime.now(),
            is_broker=is_broker,
            lead_id=lead_id
        )
        self.conv_history.add_message(lead_id, message)
        
        # Skip extraction for broker messages
        if is_broker:
            return {
                'message_saved': True,
                'extraction_skipped': True,
                'reason': 'broker_message'
            }
        
        # Extract information from customer message
        extracted = self._extract_information(message_text, response_time_seconds)
        
        # Get or create lead profile
        existing_profile = self.lead_store.get(lead_id)
        
        if existing_profile:
            # Update existing profile with new information
            updated_profile = self._merge_profile(existing_profile, extracted)
        else:
            # Create new profile
            updated_profile = self._create_profile(lead_id, extracted)
        
        # Save updated profile
        self.lead_store.save(updated_profile)
        
        return {
            'message_saved': True,
            'profile_updated': True,
            'profile': updated_profile,
            'extracted_data': extracted,
            'is_new_lead': existing_profile is None
        }
    
    def _extract_information(
        self,
        text: str,
        response_time_seconds: Optional[int] = None
    ) -> Dict[str, Any]:
        """Extract all relevant information from message text"""
        
        # Budget extraction
        budget_min, budget_max = self.extractor.extract_budget(text)
        
        # Location extraction
        locations = self.extractor.extract_locations(text)
        
        # Interest level classification
        interest_level = self.extractor.classify_interest(text, response_time_seconds)
        
        # Intent detection
        intent = self.extractor.detect_intent(text)
        
        # Property type extraction
        property_types = self.extractor.extract_property_type(text)
        
        # Bedroom count
        bedroom_count = self.extractor.extract_bedroom_count(text)
        
        # Key phrases
        key_phrases = self.extractor.extract_key_phrases(text)
        
        return {
            'budget_min': budget_min,
            'budget_max': budget_max,
            'locations': locations,
            'interest_level': interest_level,
            'intent': intent,
            'property_types': property_types,
            'bedroom_count': bedroom_count,
            'key_phrases': key_phrases
        }
    
    def _create_profile(self, lead_id: str, extracted: Dict[str, Any]) -> LeadProfile:
        """Create a new lead profile from extracted data"""
        return LeadProfile(
            lead_id=lead_id,
            budget_min=extracted['budget_min'],
            budget_max=extracted['budget_max'],
            locations=extracted['locations'],
            property_types=extracted['property_types'],
            intent=extracted['intent'],
            interest_level=extracted['interest_level'],
            key_phrases=extracted['key_phrases'],
            last_contact=datetime.now(),
            total_interactions=1
        )
    
    def _merge_profile(
        self,
        existing: LeadProfile,
        extracted: Dict[str, Any]
    ) -> LeadProfile:
        """
        Merge new extracted data with existing profile
        
        Strategy:
        - Update budget if new info is more specific
        - Append new locations (deduplicate)
        - Upgrade interest level if increased
        - Keep most specific intent
        - Increment interaction count
        """
        # Update budget if new information provided
        if extracted['budget_min'] is not None:
            existing.budget_min = extracted['budget_min']
        if extracted['budget_max'] is not None:
            existing.budget_max = extracted['budget_max']
        
        # Merge locations (deduplicate)
        new_locations = set(existing.locations + extracted['locations'])
        existing.locations = list(new_locations)
        
        # Merge property types
        new_types = set(existing.property_types + extracted['property_types'])
        existing.property_types = list(new_types)
        
        # Upgrade interest level if higher
        level_priority = {'cold': 1, 'warm': 2, 'hot': 3}
        current_priority = level_priority[existing.interest_level.value]
        new_priority = level_priority[extracted['interest_level'].value]
        
        if new_priority > current_priority:
            existing.interest_level = extracted['interest_level']
        
        # Update intent if more specific (not BROWSE)
        if extracted['intent'] != Intent.BROWSE:
            existing.intent = extracted['intent']
        
        # Merge key phrases
        new_phrases = set(existing.key_phrases + extracted['key_phrases'])
        existing.key_phrases = list(new_phrases)
        
        # Update metadata
        existing.last_contact = datetime.now()
        existing.total_interactions += 1
        
        return existing
    
    def get_lead_summary(self, lead_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a summary of the lead including recent conversation
        
        Args:
            lead_id: Lead identifier
        
        Returns:
            Dictionary with profile and recent messages, or None if not found
        """
        profile = self.lead_store.get(lead_id)
        if not profile:
            return None
        
        recent_messages = self.conv_history.get_history(lead_id, limit=10)
        
        return {
            'profile': profile,
            'recent_messages': recent_messages,
            'message_count': len(recent_messages)
        }
