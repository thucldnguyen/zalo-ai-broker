"""
Strategist Agent - Decide next best action

Responsibilities:
- Analyze lead state and conversation context
- Decide when to follow up
- Determine reply urgency and approach
- Recommend tactical direction for Closer agent

Input: Lead profile + conversation history
Output: Action recommendations (quick_reply, follow_up, wait)
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from core.models import LeadProfile, Message, InterestLevel, FollowUpTask
from core.memory import LeadStore, ConversationHistory


class StrategistAgent:
    """
    Agent that makes tactical decisions about lead engagement
    """
    
    # Follow-up timing rules (hours since last contact)
    FOLLOW_UP_INTERVALS = {
        'hot': 2,      # 2 hours for hot leads
        'warm': 24,    # 24 hours for warm leads
        'cold': 72     # 72 hours for cold leads
    }
    
    def __init__(self, lead_store: LeadStore, conversation_history: ConversationHistory):
        """
        Initialize Strategist Agent
        
        Args:
            lead_store: Storage for lead profiles
            conversation_history: Storage for conversation messages
        """
        self.lead_store = lead_store
        self.conv_history = conversation_history
    
    def decide_action(self, lead_id: str) -> Dict[str, Any]:
        """
        Decide the next best action for a lead
        
        Args:
            lead_id: Lead identifier
        
        Returns:
            Dictionary with recommended action and reasoning
        """
        profile = self.lead_store.get(lead_id)
        if not profile:
            return {
                'action': 'error',
                'reason': 'lead_not_found'
            }
        
        recent_messages = self.conv_history.get_history(lead_id, limit=5)
        
        # Check if customer asked a question
        if self._has_unanswered_question(recent_messages):
            return {
                'action': 'quick_reply',
                'priority': 'high',
                'reasoning': 'Customer asked a question - respond quickly',
                'suggested_approach': 'answer_question',
                'urgency': 'immediate'
            }
        
        # Check time since last contact
        hours_since_contact = self._hours_since_last_contact(profile)
        should_follow_up = self._should_follow_up(profile, hours_since_contact)
        
        if should_follow_up:
            follow_up_type = self._determine_follow_up_type(profile, hours_since_contact)
            return {
                'action': 'follow_up',
                'priority': self._get_priority(profile.interest_level),
                'reasoning': f"{hours_since_contact:.1f} hours since last contact - time to follow up",
                'suggested_approach': follow_up_type,
                'urgency': self._get_urgency(profile.interest_level)
            }
        
        # Check if lead engagement is declining
        if self._is_engagement_declining(recent_messages):
            return {
                'action': 'gentle_nudge',
                'priority': 'normal',
                'reasoning': 'Engagement declining - gentle re-engagement needed',
                'suggested_approach': 'value_reminder',
                'urgency': 'normal'
            }
        
        # Default: wait
        return {
            'action': 'wait',
            'priority': 'low',
            'reasoning': f'Too soon to follow up - wait {self._time_until_follow_up(profile, hours_since_contact):.1f} more hours',
            'suggested_approach': None,
            'urgency': 'none'
        }
    
    def get_follow_up_tasks(self, cutoff_hours: int = 24) -> List[FollowUpTask]:
        """
        Get all leads that need follow-up within cutoff period
        
        Args:
            cutoff_hours: Look ahead this many hours
        
        Returns:
            List of FollowUpTask objects, sorted by priority
        """
        all_leads = self.lead_store.get_all()
        tasks = []
        
        for lead in all_leads:
            hours_since = self._hours_since_last_contact(lead)
            
            if self._should_follow_up(lead, hours_since):
                # Calculate when follow-up should happen
                interval = self.FOLLOW_UP_INTERVALS[lead.interest_level.value]
                scheduled_time = lead.last_contact + timedelta(hours=interval)
                
                # Only include if within cutoff window
                hours_until = (scheduled_time - datetime.now()).total_seconds() / 3600
                if hours_until <= cutoff_hours:
                    task = FollowUpTask(
                        lead_id=lead.lead_id,
                        scheduled_time=scheduled_time,
                        priority=self._get_priority(lead.interest_level),
                        action=self._determine_follow_up_type(lead, hours_since),
                        context=f"Interest: {lead.interest_level.value}, Last contact: {hours_since:.1f}h ago"
                    )
                    tasks.append(task)
        
        # Sort by priority (hot first) then by scheduled time
        priority_order = {'high': 1, 'normal': 2, 'low': 3}
        tasks.sort(key=lambda t: (priority_order[t.priority], t.scheduled_time))
        
        return tasks
    
    def _has_unanswered_question(self, messages: List[Message]) -> bool:
        """Check if the last customer message was a question"""
        if not messages:
            return False
        
        # Get last customer message
        customer_messages = [m for m in messages if not m.is_broker]
        if not customer_messages:
            return False
        
        last_customer_msg = customer_messages[0]
        
        # Check if it's a question
        text = last_customer_msg.text.lower()
        return '?' in text or text.endswith('không') or 'có' in text[:10]
    
    def _hours_since_last_contact(self, profile: LeadProfile) -> float:
        """Calculate hours since last contact"""
        delta = datetime.now() - profile.last_contact
        return delta.total_seconds() / 3600
    
    def _should_follow_up(self, profile: LeadProfile, hours_since: float) -> bool:
        """Determine if it's time to follow up based on interest level"""
        interval = self.FOLLOW_UP_INTERVALS[profile.interest_level.value]
        return hours_since >= interval
    
    def _time_until_follow_up(self, profile: LeadProfile, hours_since: float) -> float:
        """Calculate hours until next follow-up is due"""
        interval = self.FOLLOW_UP_INTERVALS[profile.interest_level.value]
        return max(0, interval - hours_since)
    
    def _determine_follow_up_type(self, profile: LeadProfile, hours_since: float) -> str:
        """Determine the type of follow-up based on context"""
        if profile.interest_level == InterestLevel.HOT:
            if hours_since > 6:
                return 'urgent_follow_up'
            return 'quick_check_in'
        
        elif profile.interest_level == InterestLevel.WARM:
            if hours_since > 48:
                return 'value_reminder'
            return 'gentle_follow_up'
        
        else:  # COLD
            return 'soft_touch'
    
    def _get_priority(self, interest_level: InterestLevel) -> str:
        """Map interest level to priority"""
        priority_map = {
            InterestLevel.HOT: 'high',
            InterestLevel.WARM: 'normal',
            InterestLevel.COLD: 'low'
        }
        return priority_map[interest_level]
    
    def _get_urgency(self, interest_level: InterestLevel) -> str:
        """Map interest level to urgency"""
        urgency_map = {
            InterestLevel.HOT: 'immediate',
            InterestLevel.WARM: 'normal',
            InterestLevel.COLD: 'low'
        }
        return urgency_map[interest_level]
    
    def _is_engagement_declining(self, messages: List[Message]) -> bool:
        """
        Check if customer engagement is declining
        
        Signals:
        - Response rate dropping
        - Shorter messages
        - Longer response times
        """
        if len(messages) < 4:
            return False
        
        # Get customer messages only
        customer_msgs = [m for m in messages if not m.is_broker]
        
        if len(customer_msgs) < 3:
            return False
        
        # Check if messages are getting shorter
        recent_lengths = [len(m.text) for m in customer_msgs[:2]]
        older_lengths = [len(m.text) for m in customer_msgs[2:4]]
        
        if recent_lengths and older_lengths:
            avg_recent = sum(recent_lengths) / len(recent_lengths)
            avg_older = sum(older_lengths) / len(older_lengths)
            
            # Declining if recent messages are <50% of previous length
            if avg_recent < avg_older * 0.5:
                return True
        
        return False
