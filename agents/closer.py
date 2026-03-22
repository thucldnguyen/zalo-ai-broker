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

import random
from typing import List, Dict, Any, Optional

from core.models import LeadProfile, Suggestion, Intent, InterestLevel


class CloserAgent:
    """
    Agent that generates persuasive Vietnamese messages for real estate sales
    """
    
    # Message templates by tactic
    TEMPLATES = {
        'urgency': [
            "Anh {name} ơi, căn này đang có {count} khách khác quan tâm. Em sợ lỡ mất cơ hội tốt cho anh.",
            "Anh {name}, chủ nhà vừa báo có người đặt cọc rồi ạ. Anh muốn em giữ lại không ạ?",
            "Thị trường đang nóng lắm anh {name} ạ. Căn này nếu không quyết định nhanh sẽ mất ngay."
        ],
        
        'scarcity': [
            "Trong khu vực {location}, hiện chỉ còn {count} căn trong tầm giá của anh thôi ạ.",
            "Loại {property_type} view {feature} ở {location} rất hiếm anh {name} ạ. Khó tìm lắm!",
            "Giá tốt như vậy không còn nhiều đâu anh. Tuần sau chắc tăng rồi ạ."
        ],
        
        'social_proof': [
            "Tuần trước em vừa bán {count} căn cùng khu cho khách đầu tư. Giá đang tăng đều {percent}%/năm anh ạ.",
            "Nhiều khách của em ở {location} đang cho thuê sinh lời {percent}%/năm đấy anh.",
            "Anh {name}, dự án này em đã bán được {count} căn rồi. Khách đều hài lòng lắm ạ!"
        ],
        
        'value_proposition': [
            "Với budget {budget} tỷ của anh, đây là căn đáng giá nhất em tìm được ạ.",
            "Căn này có đủ {features} mà anh yêu cầu. Giá lại phù hợp nữa.",
            "So với thị trường, giá này rẻ hơn {percent}% đấy anh {name}."
        ],
        
        'objection_handling': [
            "Em hiểu anh lo về {concern}. Thực tế {counterpoint}. Nhiều khách của em ban đầu cũng lo vậy.",
            "Anh thắc mắc về {concern} đúng không ạ? Em giải thích cho anh nghe nhé.",
            "Vấn đề {concern} này em đã check kỹ rồi anh. Anh yên tâm được ạ."
        ],
        
        'limited_time_offer': [
            "Chủ nhà đồng ý giảm thêm {discount} triệu nếu anh quyết định trong tuần này ạ!",
            "Ưu đãi này chỉ còn {days} ngày nữa thôi anh {name} ạ.",
            "Em vừa check với chủ nhà, họ chỉ giữ giá này đến hết tháng thôi anh."
        ],
        
        'soft_touch': [
            "Anh {name} ơi, dạo này thị trường thế nào rồi ạ? Em có vài căn mới hay lắm.",
            "Chào anh {name}! Em nhớ anh đang quan tâm {property_type} ở {location}. Em vừa có căn phù hợp lắm ạ!",
            "Anh {name} còn đang tìm nhà không ạ? Em có tin tốt muốn chia sẻ với anh."
        ],
        
        'answer_question': [
            "Dạ câu hỏi của anh về {topic}, em xin phép giải đáp như sau:",
            "Em hiểu thắc mắc của anh rồi. Về vấn đề {topic} thì:",
            "Cảm ơn anh đã hỏi! Về {topic}, thực tế là:"
        ]
    }
    
    def __init__(self):
        """Initialize Closer Agent"""
        pass
    
    def generate_suggestions(
        self,
        profile: LeadProfile,
        approach: str,
        context: Optional[str] = None,
        count: int = 3
    ) -> List[Suggestion]:
        """
        Generate message suggestions for a lead
        
        Args:
            profile: Lead profile with preferences
            approach: Strategic approach (e.g., 'urgent_follow_up', 'answer_question')
            context: Additional context (e.g., specific question asked)
            count: Number of suggestions to generate
        
        Returns:
            List of Suggestion objects, sorted by confidence (highest first)
        """
        suggestions = []
        
        # Determine primary and secondary tactics based on approach
        tactics = self._select_tactics(approach, profile.interest_level)
        
        # Generate suggestions using different tactic combinations
        for i in range(count):
            tactic = tactics[i % len(tactics)]
            message = self._generate_message(profile, tactic, context)
            
            # Calculate confidence score
            confidence = self._calculate_confidence(profile, tactic)
            
            # Create reasoning
            reasoning = self._generate_reasoning(profile, tactic, approach)
            
            suggestion = Suggestion(
                message=message,
                tactics=[tactic],
                confidence=confidence,
                reasoning=reasoning
            )
            suggestions.append(suggestion)
        
        # Sort by confidence (highest first)
        suggestions.sort(key=lambda s: s.confidence, reverse=True)
        
        return suggestions
    
    def _select_tactics(self, approach: str, interest_level: InterestLevel) -> List[str]:
        """
        Select appropriate tactics based on approach and interest level
        
        Returns:
            List of tactic names in priority order
        """
        # Map approaches to tactics
        approach_tactics = {
            'urgent_follow_up': ['urgency', 'scarcity', 'limited_time_offer'],
            'quick_check_in': ['value_proposition', 'urgency', 'social_proof'],
            'gentle_follow_up': ['soft_touch', 'value_proposition', 'social_proof'],
            'value_reminder': ['social_proof', 'value_proposition', 'urgency'],
            'answer_question': ['answer_question', 'value_proposition', 'urgency'],
            'soft_touch': ['soft_touch', 'value_proposition'],
        }
        
        tactics = approach_tactics.get(approach, ['value_proposition', 'social_proof'])
        
        # Adjust based on interest level
        if interest_level == InterestLevel.HOT:
            # For hot leads, add urgency and scarcity
            if 'urgency' not in tactics:
                tactics.insert(0, 'urgency')
        
        return tactics
    
    def _generate_message(
        self,
        profile: LeadProfile,
        tactic: str,
        context: Optional[str] = None
    ) -> str:
        """Generate a message using specified tactic and lead profile"""
        
        # Get template for tactic
        templates = self.TEMPLATES.get(tactic, self.TEMPLATES['value_proposition'])
        template = random.choice(templates)
        
        # Build substitution dict
        substitutions = {
            'name': profile.name or 'anh',
            'count': random.randint(2, 5),
            'percent': random.randint(8, 15),
            'days': random.randint(2, 7),
            'discount': random.randint(50, 200),
        }
        
        # Add profile-specific data
        if profile.locations:
            substitutions['location'] = profile.locations[0]
        else:
            substitutions['location'] = 'khu vực'
        
        if profile.property_types:
            type_map = {
                'apartment': 'căn hộ',
                'villa': 'biệt thự',
                'land': 'đất nền',
                'office': 'văn phòng'
            }
            substitutions['property_type'] = type_map.get(
                profile.property_types[0],
                'căn hộ'
            )
        else:
            substitutions['property_type'] = 'căn hộ'
        
        if profile.budget_min and profile.budget_max:
            avg_budget = (profile.budget_min + profile.budget_max) / 2
            substitutions['budget'] = f"{avg_budget / 1_000_000_000:.1f}"
        else:
            substitutions['budget'] = "2-3"
        
        # Features from key phrases
        if profile.key_phrases:
            substitutions['feature'] = profile.key_phrases[0]
            substitutions['features'] = ', '.join(profile.key_phrases[:3])
        else:
            substitutions['feature'] = 'đẹp'
            substitutions['features'] = 'vị trí đẹp, view thoáng'
        
        # Context-specific substitutions
        if context:
            substitutions['topic'] = context
            substitutions['concern'] = context
            substitutions['counterpoint'] = 'điều này hoàn toàn bình thường ạ'
        
        # Apply substitutions
        try:
            message = template.format(**substitutions)
        except KeyError:
            # Fallback if template variable not available
            message = template
            for key, value in substitutions.items():
                message = message.replace(f"{{{key}}}", str(value))
        
        return message
    
    def _calculate_confidence(self, profile: LeadProfile, tactic: str) -> float:
        """
        Calculate confidence score for tactic given lead profile
        
        Returns:
            Confidence score between 0.0 and 1.0
        """
        base_confidence = 0.7
        
        # Adjust based on profile completeness
        if profile.name:
            base_confidence += 0.05
        if profile.budget_min and profile.budget_max:
            base_confidence += 0.05
        if profile.locations:
            base_confidence += 0.05
        if profile.key_phrases:
            base_confidence += 0.05
        
        # Adjust based on tactic fit with interest level
        tactic_fit = {
            InterestLevel.HOT: {
                'urgency': 0.15,
                'scarcity': 0.10,
                'limited_time_offer': 0.12
            },
            InterestLevel.WARM: {
                'value_proposition': 0.10,
                'social_proof': 0.08,
                'soft_touch': 0.05
            },
            InterestLevel.COLD: {
                'soft_touch': 0.08,
                'value_proposition': 0.05
            }
        }
        
        fit_bonus = tactic_fit.get(profile.interest_level, {}).get(tactic, 0)
        final_confidence = min(1.0, base_confidence + fit_bonus)
        
        return round(final_confidence, 2)
    
    def _generate_reasoning(
        self,
        profile: LeadProfile,
        tactic: str,
        approach: str
    ) -> str:
        """Generate human-readable reasoning for the suggestion"""
        
        reasons = []
        
        # Interest level reasoning
        if profile.interest_level == InterestLevel.HOT:
            reasons.append("Lead is HOT - needs immediate attention")
        elif profile.interest_level == InterestLevel.WARM:
            reasons.append("Lead is WARM - maintain engagement")
        
        # Tactic reasoning
        tactic_reasons = {
            'urgency': 'Create urgency to drive decision',
            'scarcity': 'Emphasize limited availability',
            'social_proof': 'Build trust through others\' success',
            'value_proposition': 'Highlight value match to needs',
            'limited_time_offer': 'Time-bound incentive to act',
            'soft_touch': 'Gentle re-engagement without pressure'
        }
        
        if tactic in tactic_reasons:
            reasons.append(tactic_reasons[tactic])
        
        # Profile-based reasoning
        if profile.total_interactions > 5:
            reasons.append("Established relationship - can be direct")
        if profile.budget_min:
            reasons.append("Budget known - can be specific")
        
        return " | ".join(reasons)
