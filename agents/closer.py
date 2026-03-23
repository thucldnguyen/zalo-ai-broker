"""
Closer Agent - Generate persuasive Vietnamese messages

Responsibilities:
- Generate reply suggestions in Vietnamese
- Apply persuasion tactics (urgency, scarcity, social proof)
- Personalize messages based on lead profile
- Score suggestions by confidence

Input: Lead profile + strategic approach
Output: Multiple message suggestions with tactics and confidence scores
"""

import logging
import random
from typing import List, Dict, Any, Optional

from core.models import LeadProfile, Message, Suggestion, Intent, InterestLevel

logger = logging.getLogger(__name__)


class CloserAgent:
    """
    Agent that generates persuasive Vietnamese messages for real estate sales.

    When an LLMProvider is injected, reply drafting is fully model-driven
    and grounded in the actual conversation.  If the LLM is unavailable the
    agent falls back to the rule-based template system.
    """

    # ------------------------------------------------------------------
    # Template fallback (kept as heuristic baseline)
    # ------------------------------------------------------------------

    TEMPLATES = {
        "urgency": [
            "Anh {name} ơi, căn này đang có khách khác quan tâm. Em sợ lỡ mất cơ hội tốt cho anh.",
            "Anh {name}, chủ nhà vừa báo có người đặt cọc rồi ạ. Anh muốn em giữ lại không ạ?",
            "Thị trường đang nóng lắm anh {name} ạ. Căn này nếu không quyết định nhanh sẽ mất ngay.",
        ],
        "scarcity": [
            "Trong khu vực {location}, hiện không còn nhiều căn trong tầm giá của anh ạ.",
            "Loại {property_type} ở {location} rất hiếm anh {name} ạ. Khó tìm lắm!",
            "Giá tốt như vậy không còn nhiều đâu anh. Tuần sau chắc tăng rồi ạ.",
        ],
        "social_proof": [
            "Nhiều khách của em ở {location} rất hài lòng với khu vực này anh ạ.",
            "Anh {name}, khu này em đã tư vấn nhiều khách rồi. Mọi người đều hài lòng lắm ạ!",
        ],
        "value_proposition": [
            "Với budget của anh, đây là căn đáng giá nhất em tìm được ạ.",
            "Căn này có đủ {features} mà anh yêu cầu. Giá lại phù hợp nữa.",
        ],
        "objection_handling": [
            "Em hiểu anh đang cân nhắc. Anh cứ hỏi thêm em nhé, em sẵn sàng giải đáp ạ.",
            "Anh thắc mắc điều gì em giải thích thêm cho anh nghe nhé.",
        ],
        "limited_time_offer": [
            "Chủ nhà đang xem xét giá, anh quyết định sớm thì có lợi hơn ạ.",
            "Ưu đãi này không kéo dài lâu đâu anh {name} ạ.",
        ],
        "soft_touch": [
            "Anh {name} ơi, dạo này thị trường thế nào rồi ạ? Em có vài căn mới hay lắm.",
            "Chào anh {name}! Em nhớ anh đang quan tâm {property_type} ở {location}. Em vừa có căn phù hợp lắm ạ!",
            "Anh {name} còn đang tìm nhà không ạ? Em có tin tốt muốn chia sẻ với anh.",
        ],
        "answer_question": [
            "Dạ câu hỏi của anh, em xin phép giải đáp như sau:",
            "Em hiểu thắc mắc của anh rồi. Để em giải thích chi tiết hơn nhé:",
            "Cảm ơn anh đã hỏi! Về vấn đề này, thực tế là:",
        ],
    }

    def __init__(self, llm_provider=None) -> None:
        """
        Args:
            llm_provider: Optional[LLMProvider] – if provided, reply drafting uses
                          the Anthropic Messages API; otherwise uses templates.
        """
        self._llm_provider = llm_provider

    async def generate_suggestions(
        self,
        profile: LeadProfile,
        approach: str,
        context: Optional[str] = None,
        count: int = 3,
        history: Optional[List[Message]] = None,
    ) -> List[Suggestion]:
        """
        Generate message suggestions for a lead.

        Args:
            profile: Lead profile with preferences
            approach: Strategic approach (e.g. 'urgent_follow_up', 'answer_question')
            context: Additional context text (e.g. the question the customer asked)
            count: Number of suggestions to generate
            history: Recent conversation messages for LLM context

        Returns:
            List of Suggestion objects, sorted by confidence (highest first)
        """
        tactics = self._select_tactics(approach, profile.interest_level)

        if self._llm_provider is not None:
            try:
                llm_outputs = await self._llm_provider.generate_suggestions(
                    profile=profile,
                    approach=approach,
                    history=history or [],
                    tactics=tactics,
                    count=count,
                )
                suggestions = [
                    Suggestion(
                        message=out.message,
                        tactics=out.tactics,
                        confidence=self._calculate_confidence(
                            profile,
                            out.tactics[0] if out.tactics else "value_proposition",
                        ),
                        reasoning=out.reasoning,
                    )
                    for out in llm_outputs
                ]
                suggestions.sort(key=lambda s: s.confidence, reverse=True)
                return suggestions
            except Exception as exc:
                logger.warning(
                    "LLM reply generation failed, falling back to templates: %s", exc
                )

        return self._generate_from_templates(profile, approach, context, count, tactics)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _select_tactics(self, approach: str, interest_level: InterestLevel) -> List[str]:
        """Select appropriate tactics based on approach and interest level."""
        approach_tactics: Dict[str, List[str]] = {
            "urgent_follow_up": ["urgency", "scarcity", "limited_time_offer"],
            "quick_check_in": ["value_proposition", "urgency", "social_proof"],
            "gentle_follow_up": ["soft_touch", "value_proposition", "social_proof"],
            "value_reminder": ["social_proof", "value_proposition", "urgency"],
            "answer_question": ["answer_question", "value_proposition", "urgency"],
            "soft_touch": ["soft_touch", "value_proposition"],
        }
        tactics = list(approach_tactics.get(approach, ["value_proposition", "social_proof"]))

        if interest_level == InterestLevel.HOT and "urgency" not in tactics:
            tactics.insert(0, "urgency")

        return tactics

    def _generate_from_templates(
        self,
        profile: LeadProfile,
        approach: str,
        context: Optional[str],
        count: int,
        tactics: List[str],
    ) -> List[Suggestion]:
        """Template-based fallback: deterministic substitution, no fabricated numbers."""
        suggestions = []
        for i in range(count):
            tactic = tactics[i % len(tactics)]
            message = self._generate_message(profile, tactic, context)
            confidence = self._calculate_confidence(profile, tactic)
            reasoning = self._generate_reasoning(profile, tactic, approach)
            suggestions.append(
                Suggestion(
                    message=message,
                    tactics=[tactic],
                    confidence=confidence,
                    reasoning=reasoning,
                )
            )
        suggestions.sort(key=lambda s: s.confidence, reverse=True)
        return suggestions

    def _generate_message(
        self,
        profile: LeadProfile,
        tactic: str,
        context: Optional[str] = None,
    ) -> str:
        templates = self.TEMPLATES.get(tactic, self.TEMPLATES["value_proposition"])
        template = random.choice(templates)

        substitutions: Dict[str, Any] = {
            "name": profile.name or "anh",
        }

        substitutions["location"] = profile.locations[0] if profile.locations else "khu vực"

        type_map = {
            "apartment": "căn hộ",
            "villa": "biệt thự",
            "land": "đất nền",
            "office": "văn phòng",
        }
        substitutions["property_type"] = (
            type_map.get(profile.property_types[0], "căn hộ")
            if profile.property_types
            else "căn hộ"
        )

        substitutions["features"] = (
            ", ".join(profile.key_phrases[:3]) if profile.key_phrases else "vị trí đẹp, view thoáng"
        )

        if context:
            substitutions["topic"] = context
            substitutions["concern"] = context

        try:
            return template.format(**substitutions)
        except KeyError:
            message = template
            for key, value in substitutions.items():
                message = message.replace(f"{{{key}}}", str(value))
            return message

    def _calculate_confidence(self, profile: LeadProfile, tactic: str) -> float:
        """Calculate confidence score based on profile completeness and tactic fit."""
        base = 0.7
        if profile.name:
            base += 0.05
        if profile.budget_min and profile.budget_max:
            base += 0.05
        if profile.locations:
            base += 0.05
        if profile.key_phrases:
            base += 0.05

        tactic_fit = {
            InterestLevel.HOT: {"urgency": 0.15, "scarcity": 0.10, "limited_time_offer": 0.12},
            InterestLevel.WARM: {"value_proposition": 0.10, "social_proof": 0.08, "soft_touch": 0.05},
            InterestLevel.COLD: {"soft_touch": 0.08, "value_proposition": 0.05},
        }
        base += tactic_fit.get(profile.interest_level, {}).get(tactic, 0)
        return round(min(1.0, base), 2)

    def _generate_reasoning(
        self, profile: LeadProfile, tactic: str, approach: str
    ) -> str:
        reasons = []
        if profile.interest_level == InterestLevel.HOT:
            reasons.append("Lead is HOT - needs immediate attention")
        elif profile.interest_level == InterestLevel.WARM:
            reasons.append("Lead is WARM - maintain engagement")

        tactic_reasons = {
            "urgency": "Create urgency to drive decision",
            "scarcity": "Emphasize limited availability",
            "social_proof": "Build trust through others' success",
            "value_proposition": "Highlight value match to needs",
            "limited_time_offer": "Time-bound incentive to act",
            "soft_touch": "Gentle re-engagement without pressure",
            "answer_question": "Directly address customer's question",
        }
        if tactic in tactic_reasons:
            reasons.append(tactic_reasons[tactic])

        if profile.total_interactions > 5:
            reasons.append("Established relationship - can be direct")
        if profile.budget_min:
            reasons.append("Budget known - can be specific")

        return " | ".join(reasons)
