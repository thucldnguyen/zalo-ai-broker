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

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from core.models import LeadProfile, Message, Intent, InterestLevel
from core.vietnamese_nlp import VietnameseExtractor
from core.memory import LeadStore, ConversationHistory

logger = logging.getLogger(__name__)


class ListenerAgent:
    """
    Agent that listens to conversations and extracts structured data.

    Extraction priority:
    1. AnthropicLLMProvider (if injected and ANTHROPIC_API_KEY is set)
    2. VietnameseExtractor heuristics (fallback / offline)
    """

    def __init__(
        self,
        lead_store: LeadStore,
        conversation_history: ConversationHistory,
        llm_provider=None,  # Optional[LLMProvider] – avoid import cycle at module level
    ):
        self.extractor = VietnameseExtractor()
        self.lead_store = lead_store
        self.conv_history = conversation_history
        self._llm_provider = llm_provider

    async def process_message(
        self,
        message_text: str,
        lead_id: str,
        is_broker: bool = False,
        response_time_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Process an incoming message and update lead profile.

        Args:
            message_text: The message text
            lead_id: Unique identifier for the lead
            is_broker: True if message is from broker, False if from customer
            response_time_seconds: Time customer took to respond (for interest scoring)

        Returns:
            Dictionary with extracted data and updated profile
        """
        message = Message(
            text=message_text,
            timestamp=datetime.now(),
            is_broker=is_broker,
            lead_id=lead_id,
        )
        self.conv_history.add_message(lead_id, message)

        if is_broker:
            return {
                "message_saved": True,
                "extraction_skipped": True,
                "reason": "broker_message",
            }

        # Fetch recent history for LLM context (excludes the message just saved)
        history = self.conv_history.get_history(lead_id, limit=5)

        extracted = await self._extract_information(
            message_text, history, response_time_seconds
        )

        existing_profile = self.lead_store.get(lead_id)
        if existing_profile:
            updated_profile = self._merge_profile(existing_profile, extracted)
        else:
            updated_profile = self._create_profile(lead_id, extracted)

        self.lead_store.save(updated_profile)

        return {
            "message_saved": True,
            "profile_updated": True,
            "profile": updated_profile,
            "extracted_data": extracted,
            "is_new_lead": existing_profile is None,
        }

    async def _extract_information(
        self,
        text: str,
        history: List[Message],
        response_time_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Extract all relevant information from message text.

        Tries LLM first; falls back to heuristics on failure or when no provider.
        """
        if self._llm_provider is not None:
            try:
                extraction = await self._llm_provider.extract_message(
                    text, history, response_time_seconds
                )
                return {
                    "budget_min": extraction.budget_min,
                    "budget_max": extraction.budget_max,
                    "locations": extraction.locations,
                    "interest_level": InterestLevel(extraction.interest_level),
                    "intent": Intent(extraction.intent),
                    "property_types": extraction.property_types,
                    "bedroom_count": extraction.bedroom_count,
                    "key_phrases": extraction.key_phrases,
                }
            except Exception as exc:
                logger.warning(
                    "LLM extraction failed for lead, falling back to heuristics: %s", exc
                )

        # Heuristic fallback (VietnameseExtractor)
        budget_min, budget_max = self.extractor.extract_budget(text)
        return {
            "budget_min": budget_min,
            "budget_max": budget_max,
            "locations": self.extractor.extract_locations(text),
            "interest_level": self.extractor.classify_interest(text, response_time_seconds),
            "intent": self.extractor.detect_intent(text),
            "property_types": self.extractor.extract_property_type(text),
            "bedroom_count": self.extractor.extract_bedroom_count(text),
            "key_phrases": self.extractor.extract_key_phrases(text),
        }

    def _create_profile(self, lead_id: str, extracted: Dict[str, Any]) -> LeadProfile:
        """Create a new lead profile from extracted data."""
        return LeadProfile(
            lead_id=lead_id,
            budget_min=extracted["budget_min"],
            budget_max=extracted["budget_max"],
            locations=extracted["locations"],
            property_types=extracted["property_types"],
            intent=extracted["intent"],
            interest_level=extracted["interest_level"],
            key_phrases=extracted["key_phrases"],
            last_contact=datetime.now(),
            total_interactions=1,
        )

    def _merge_profile(
        self,
        existing: LeadProfile,
        extracted: Dict[str, Any],
    ) -> LeadProfile:
        """
        Merge new extracted data with existing profile.

        Strategy:
        - Update budget if new info is more specific
        - Append new locations (deduplicate)
        - Upgrade interest level if increased
        - Keep most specific intent
        - Increment interaction count
        """
        if extracted["budget_min"] is not None:
            existing.budget_min = extracted["budget_min"]
        if extracted["budget_max"] is not None:
            existing.budget_max = extracted["budget_max"]

        new_locations = set(existing.locations + extracted["locations"])
        existing.locations = list(new_locations)

        new_types = set(existing.property_types + extracted["property_types"])
        existing.property_types = list(new_types)

        level_priority = {"cold": 1, "warm": 2, "hot": 3}
        if (
            level_priority[extracted["interest_level"].value]
            > level_priority[existing.interest_level.value]
        ):
            existing.interest_level = extracted["interest_level"]

        if extracted["intent"] != Intent.BROWSE:
            existing.intent = extracted["intent"]

        new_phrases = set(existing.key_phrases + extracted["key_phrases"])
        existing.key_phrases = list(new_phrases)

        existing.last_contact = datetime.now()
        existing.total_interactions += 1

        return existing

    def get_lead_summary(self, lead_id: str) -> Optional[Dict[str, Any]]:
        """Get a summary of the lead including recent conversation."""
        profile = self.lead_store.get(lead_id)
        if not profile:
            return None

        recent_messages = self.conv_history.get_history(lead_id, limit=10)
        return {
            "profile": profile,
            "recent_messages": recent_messages,
            "message_count": len(recent_messages),
        }
