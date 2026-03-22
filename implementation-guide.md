# Zalo AI Broker Assistant - Implementation Guide

## Quick Start (Day 1)

### Project Structure
```
zalo-ai-broker/
├── agents/
│   ├── listener.py
│   ├── strategist.py
│   └── closer.py
├── core/
│   ├── memory.py
│   ├── models.py
│   └── vietnamese_nlp.py
├── data/
│   └── leads/
├── templates/
│   └── messages.json
├── tests/
├── main.py
└── requirements.txt
```

### Core Models (models.py)
```python
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict
from enum import Enum

class Intent(Enum):
    BUY = "buy"
    INVEST = "invest"
    RENT = "rent"
    BROWSE = "browse"

class InterestLevel(Enum):
    HOT = "hot"      # Ready to buy, urgent
    WARM = "warm"    # Interested, researching
    COLD = "cold"    # Just browsing

@dataclass
class LeadProfile:
    lead_id: str
    name: Optional[str]
    phone: Optional[str]
    budget_min: Optional[int]
    budget_max: Optional[int]
    locations: List[str]
    intent: Intent
    interest_level: InterestLevel
    last_contact: datetime
    
@dataclass
class Message:
    text: str
    timestamp: datetime
    is_broker: bool
    
@dataclass
class Suggestion:
    message: str
    tactics: List[str]
    confidence: float
```

### Vietnamese NLP Utilities (vietnamese_nlp.py)
```python
import re
from typing import Tuple, List, Optional

class VietnameseExtractor:
    # Budget patterns
    BUDGET_PATTERNS = [
        (r'(\d+)\s*-\s*(\d+)\s*tỷ', 1_000_000_000),
        (r'tầm\s*(\d+)\s*tỷ', 1_000_000_000),
        (r'khoảng\s*(\d+\.?\d*)\s*tỷ', 1_000_000_000),
        (r'(\d+)\s*triệu', 1_000_000),
    ]
    
    # Location keywords
    LOCATION_KEYWORDS = {
        'districts': ['quận \d+', 'q\d+', 'thủ đức', 'bình thạnh', 'phú nhuận'],
        'areas': ['thảo điền', 'an phú', 'bình an', 'cát lái'],
        'projects': ['vinhomes', 'masteri', 'gateway', 'feliz en vista']
    }
    
    # Interest signals
    HOT_SIGNALS = ['cần gấp', 'trong tuần', 'càng sớm càng tốt', 'urgent']
    WARM_SIGNALS = ['đang tìm', 'quan tâm', 'muốn xem', 'cho em thông tin']
    
    def extract_budget(self, text: str) -> Tuple[Optional[int], Optional[int]]:
        """Extract budget range from Vietnamese text"""
        text = text.lower()
        
        for pattern, multiplier in self.BUDGET_PATTERNS:
            match = re.search(pattern, text)
            if match:
                if match.lastindex == 2:  # Range
                    return (
                        int(float(match.group(1)) * multiplier),
                        int(float(match.group(2)) * multiplier)
                    )
                else:  # Single value - create range ±15%
                    value = int(float(match.group(1)) * multiplier)
                    return (int(value * 0.85), int(value * 1.15))
        
        return (None, None)
    
    def extract_locations(self, text: str) -> List[str]:
        """Extract location mentions"""
        text = text.lower()
        locations = []
        
        for category, patterns in self.LOCATION_KEYWORDS.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    locations.append(pattern)
        
        return locations
    
    def classify_interest(self, text: str, response_time: Optional[int] = None) -> InterestLevel:
        """Classify interest level based on text and behavior"""
        text = text.lower()
        
        # Check for hot signals
        if any(signal in text for signal in self.HOT_SIGNALS):
            return InterestLevel.HOT
        
        # Quick response indicates interest
        if response_time and response_time < 300:  # 5 minutes
            return InterestLevel.HOT
        
        # Check warm signals
        if any(signal in text for signal in self.WARM_SIGNALS):
            return InterestLevel.WARM
            
        return InterestLevel.COLD
```

### Listener Agent (listener.py)
```python
from datetime import datetime
from typing import Dict, Any
from core.models import LeadProfile, Message, Intent, InterestLevel
from core.vietnamese_nlp import VietnameseExtractor

class ListenerAgent:
    def __init__(self):
        self.extractor = VietnameseExtractor()
    
    def process_message(self, 
                       message: str, 
                       lead_id: str,
                       existing_profile: Optional[LeadProfile] = None) -> Dict[str, Any]:
        """Extract structured data from message"""
        
        # Extract components
        budget_min, budget_max = self.extractor.extract_budget(message)
        locations = self.extractor.extract_locations(message)
        interest = self.extractor.classify_interest(message)
        
        # Detect intent
        intent = self._detect_intent(message)
        
        # Extract name if possible
        name = self._extract_name(message)
        
        # Update or create profile
        if existing_profile:
            # Merge new data with existing
            profile = self._merge_profiles(existing_profile, {
                'budget_min': budget_min,
                'budget_max': budget_max,
                'locations': locations,
                'intent': intent,
                'interest_level': interest,
                'name': name
            })
        else:
            profile = LeadProfile(
                lead_id=lead_id,
                name=name,
                phone=None,
                budget_min=budget_min,
                budget_max=budget_max,
                locations=locations,
                intent=intent,
                interest_level=interest,
                last_contact=datetime.now()
            )
        
        return {
            'profile': profile,
            'extracted_data': {
                'budget_range': (budget_min, budget_max),
                'locations': locations,
                'intent': intent.value,
                'interest_level': interest.value,
                'key_phrases': self._extract_key_phrases(message)
            }
        }
    
    def _detect_intent(self, text: str) -> Intent:
        """Detect customer intent"""
        text = text.lower()
        
        if any(word in text for word in ['mua', 'sở hữu', 'chính chủ']):
            return Intent.BUY
        elif any(word in text for word in ['đầu tư', 'sinh lời', 'cho thuê']):
            return Intent.INVEST
        elif any(word in text for word in ['thuê', 'rent']):
            return Intent.RENT
        else:
            return Intent.BROWSE
    
    def _extract_name(self, text: str) -> Optional[str]:
        """Try to extract customer name"""
        # Simple pattern matching for Vietnamese names
        patterns = [
            r'tôi là ([A-Z][a-z]+ [A-Z][a-z]+)',
            r'mình là ([A-Z][a-z]+ [A-Z][a-z]+)',
            r'anh ([A-Z][a-z]+)',
            r'chị ([A-Z][a-z]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return None
```

### Strategist Agent (strategist.py)
```python
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from core.models import LeadProfile, InterestLevel

class StrategistAgent:
    # Follow-up rules
    FOLLOW_UP_RULES = {
        InterestLevel.HOT: {
            'max_wait_hours': 2,
            'approach': 'urgent_close',
            'max_attempts': 3
        },
        InterestLevel.WARM: {
            'max_wait_hours': 24,
            'approach': 'nurture',
            'max_attempts': 2
        },
        InterestLevel.COLD: {
            'max_wait_hours': 72,
            'approach': 'reactivate',
            'max_attempts': 1
        }
    }
    
    def decide_action(self, 
                     lead: LeadProfile,
                     last_message_from_customer: bool,
                     conversation_history: List[Message]) -> Dict[str, Any]:
        """Decide next best action"""
        
        hours_since_contact = (datetime.now() - lead.last_contact).total_seconds() / 3600
        rules = self.FOLLOW_UP_RULES[lead.interest_level]
        
        # Immediate response if customer just messaged
        if last_message_from_customer and hours_since_contact < 0.1:
            return {
                'action': 'quick_reply',
                'priority': 'high',
                'approach': self._select_approach(lead, conversation_history),
                'reasoning': 'Customer just messaged - respond immediately'
            }
        
        # Follow-up needed?
        if hours_since_contact > rules['max_wait_hours']:
            attempts = self._count_recent_attempts(conversation_history)
            if attempts < rules['max_attempts']:
                return {
                    'action': 'follow_up',
                    'priority': 'medium',
                    'approach': rules['approach'],
                    'reasoning': f'No contact for {int(hours_since_contact)} hours'
                }
        
        # Wait
        return {
            'action': 'wait',
            'priority': 'low',
            'approach': None,
            'reasoning': 'Recent contact, no action needed'
        }
    
    def _select_approach(self, lead: LeadProfile, history: List[Message]) -> str:
        """Select messaging approach based on context"""
        
        # Check last customer message
        if history:
            last_customer_msg = next((m for m in reversed(history) if not m.is_broker), None)
            if last_customer_msg:
                text = last_customer_msg.text.lower()
                
                # Question about price
                if any(word in text for word in ['giá', 'bao nhiêu', 'price']):
                    return 'price_negotiation'
                
                # Question about viewing
                if any(word in text for word in ['xem', 'visit', 'khi nào']):
                    return 'schedule_viewing'
                
                # Objection
                if any(word in text for word in ['đắt', 'xa', 'không ưng']):
                    return 'handle_objection'
        
        # Default based on interest
        if lead.interest_level == InterestLevel.HOT:
            return 'create_urgency'
        elif lead.interest_level == InterestLevel.WARM:
            return 'build_trust'
        else:
            return 'reactivate_interest'
```

### Closer Agent (closer.py)
```python
import json
import random
from typing import List, Dict, Any
from core.models import Suggestion, LeadProfile

class CloserAgent:
    def __init__(self, template_path: str = 'templates/messages.json'):
        with open(template_path, 'r', encoding='utf-8') as f:
            self.templates = json.load(f)
    
    def generate_suggestions(self,
                           lead: LeadProfile,
                           approach: str,
                           context: Dict[str, Any]) -> List[Suggestion]:
        """Generate 2-3 message suggestions"""
        
        suggestions = []
        
        # Get templates for approach
        approach_templates = self.templates.get(approach, self.templates['default'])
        
        # Generate variations
        for i in range(min(3, len(approach_templates))):
            template = approach_templates[i]
            message = self._personalize_message(template, lead, context)
            
            suggestion = Suggestion(
                message=message,
                tactics=self._identify_tactics(message),
                confidence=self._calculate_confidence(lead, approach)
            )
            suggestions.append(suggestion)
        
        return sorted(suggestions, key=lambda x: x.confidence, reverse=True)[:2]
    
    def _personalize_message(self, 
                           template: str, 
                           lead: LeadProfile,
                           context: Dict[str, Any]) -> str:
        """Personalize template with lead data"""
        
        replacements = {
            '{name}': lead.name or 'anh/chị',
            '{location}': lead.locations[0] if lead.locations else 'khu vực anh/chị quan tâm',
            '{budget}': self._format_budget(lead.budget_min, lead.budget_max),
            '{intent}': self._format_intent(lead.intent),
        }
        
        # Add context-specific replacements
        if 'property_count' in context:
            replacements['{count}'] = str(context['property_count'])
        
        if 'discount' in context:
            replacements['{discount}'] = f"{context['discount']}tr"
        
        message = template
        for key, value in replacements.items():
            message = message.replace(key, value)
        
        return message
    
    def _format_budget(self, min_budget: Optional[int], max_budget: Optional[int]) -> str:
        """Format budget in Vietnamese style"""
        if not min_budget:
            return "ngân sách của anh/chị"
        
        if min_budget == max_budget:
            return f"{min_budget / 1_000_000_000:.1f} tỷ"
        else:
            return f"{min_budget / 1_000_000_000:.1f}-{max_budget / 1_000_000_000:.1f} tỷ"
```

### Message Templates (templates/messages.json)
```json
{
  "create_urgency": [
    "Anh {name} ơi, căn {location} em vừa gửi đang có 2 khách khác quan tâm. Em sợ lỡ mất cơ hội tốt cho anh. Anh có muốn em giữ lại để mình xem chiều nay không ạ?",
    "Chào anh {name}, căn này tuần trước giá còn thấp hơn 50tr. Chủ nhà vừa tăng giá vì nhiều người hỏi quá. Anh quyết định nhanh em xin được giá cũ cho anh nhé!",
    "Anh {name} à, em mới nhận tin từ chủ nhà là có người đặt cọc rồi. Nhưng họ chưa chốt. Anh quan tâm thật em can thiệp giúp anh nhé!"
  ],
  
  "build_trust": [
    "Anh {name}, em gửi anh xem thêm 3 căn {location} trong tầm {budget}. Em đã tự đi xem và chọn những căn đẹp nhất. Anh xem căn nào ưng ý em sắp xếp xem ngay nhé!",
    "Chào anh {name}, em vừa tư vấn cho 1 anh khách cũng tìm {location} như anh. Anh ấy rất hài lòng với căn em gợi ý. Em gửi anh tham khảo luôn nhé!",
    "Anh {name} ơi, {location} đang có chính sách ưu đãi cho khách {intent}. Em tổng hợp những căn tốt nhất gửi anh. Có gì thắc mắc anh cứ hỏi em nhé!"
  ],
  
  "handle_objection": [
    "Em hiểu anh {name} lo về giá. Thực tế so với khu vực, căn này đang rẻ hơn 10-15%. Em có thể thương lượng thêm với chủ nhà nếu anh thật sự quan tâm ạ.",
    "Anh {name} à, em hiểu {location} hơi xa trung tâm. Nhưng Metro sắp xong, giá chắc chắn tăng 20-30%. Nhiều khách của em mua từ năm ngoái giờ lãi rồi anh ạ!",
    "Dạ anh {name}, em có căn khác phù hợp hơn với ngân sách của anh. Vẫn ở {location} nhưng giá mềm hơn. Anh muốn xem không ạ?"
  ],
  
  "schedule_viewing": [
    "Dạ anh {name}, em có thể sắp xếp cho anh xem vào chiều nay hoặc sáng mai. Anh tiện giờ nào ạ? Em book lịch với chủ nhà luôn cho anh nhé!",
    "Anh {name} ơi, cuối tuần này em organize tour xem nhà cho 3-4 khách cùng khu {location}. Anh đi cùng luôn cho tiện, xem nhiều căn 1 lúc để so sánh ạ!",
    "Chào anh {name}, em sắp xếp được lịch xem căn anh thích rồi. Thứ 7 này 9h sáng hoặc 2h chiều anh chọn giờ nào ạ?"
  ],
  
  "follow_up": [
    "Anh {name} ơi, hôm qua em gửi thông tin căn {location} mà anh chưa phản hồi. Anh xem có ưng ý không ạ? Căn này đang hot lắm anh à!",
    "Chào anh {name}, em follow up về căn {budget} ở {location} em gửi hôm trước. Anh còn quan tâm không ạ? Giá vẫn giữ nguyên cho anh nè!",
    "Anh {name} à, em biết anh bận. Nhưng căn {location} này thật sự rất tốt cho {intent}. Anh dành 30 phút xem với em được không ạ?"
  ]
}
```

### Memory Store (memory.py)
```python
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from core.models import LeadProfile, Message

class LeadMemoryStore:
    def __init__(self, data_dir: str = 'data/leads'):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
    
    def save_lead(self, lead: LeadProfile) -> None:
        """Save lead profile to JSON"""
        file_path = os.path.join(self.data_dir, f"{lead.lead_id}.json")
        
        lead_data = {
            'lead_id': lead.lead_id,
            'name': lead.name,
            'phone': lead.phone,
            'budget_min': lead.budget_min,
            'budget_max': lead.budget_max,
            'locations': lead.locations,
            'intent': lead.intent.value,
            'interest_level': lead.interest_level.value,
            'last_contact': lead.last_contact.isoformat()
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(lead_data, f, ensure_ascii=False, indent=2)
    
    def load_lead(self, lead_id: str) -> Optional[LeadProfile]:
        """Load lead profile from JSON"""
        file_path = os.path.join(self.data_dir, f"{lead_id}.json")
        
        if not os.path.exists(file_path):
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return LeadProfile(
            lead_id=data['lead_id'],
            name=data.get('name'),
            phone=data.get('phone'),
            budget_min=data.get('budget_min'),
            budget_max=data.get('budget_max'),
            locations=data.get('locations', []),
            intent=Intent(data['intent']),
            interest_level=InterestLevel(data['interest_level']),
            last_contact=datetime.fromisoformat(data['last_contact'])
        )
    
    def save_conversation(self, lead_id: str, messages: List[Message]) -> None:
        """Save conversation history"""
        file_path = os.path.join(self.data_dir, f"{lead_id}_conversation.json")
        
        conv_data = [
            {
                'text': msg.text,
                'timestamp': msg.timestamp.isoformat(),
                'is_broker': msg.is_broker
            }
            for msg in messages
        ]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(conv_data, f, ensure_ascii=False, indent=2)
    
    def get_active_leads(self, hours: int = 72) -> List[LeadProfile]:
        """Get leads active in last N hours"""
        active_leads = []
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        for filename in os.listdir(self.data_dir):
            if filename.endswith('.json') and not filename.endswith('_conversation.json'):
                lead_id = filename.replace('.json', '')
                lead = self.load_lead(lead_id)
                
                if lead and lead.last_contact > cutoff_time:
                    active_leads.append(lead)
        
        return sorted(active_leads, key=lambda x: x.last_contact, reverse=True)
```

### Main Application (main.py)
```python
from datetime import datetime
from typing import List
from agents.listener import ListenerAgent
from agents.strategist import StrategistAgent
from agents.closer import CloserAgent
from core.memory import LeadMemoryStore
from core.models import Message

class ZaloAIBroker:
    def __init__(self):
        self.listener = ListenerAgent()
        self.strategist = StrategistAgent()
        self.closer = CloserAgent()
        self.memory = LeadMemoryStore()
    
    def process_conversation(self, lead_id: str, new_message: str, is_broker: bool = False):
        """Process new message in conversation"""
        
        # Load existing profile
        lead_profile = self.memory.load_lead(lead_id)
        
        # Create message object
        message = Message(
            text=new_message,
            timestamp=datetime.now(),
            is_broker=is_broker
        )
        
        if not is_broker:
            # Customer message - extract info
            result = self.listener.process_message(
                new_message, 
                lead_id,
                lead_profile
            )
            
            # Save updated profile
            self.memory.save_lead(result['profile'])
            
            # Decide action
            action = self.strategist.decide_action(
                result['profile'],
                last_message_from_customer=True,
                conversation_history=[]  # Load from memory in real impl
            )
            
            # Generate suggestions if needed
            if action['action'] in ['quick_reply', 'follow_up']:
                suggestions = self.closer.generate_suggestions(
                    result['profile'],
                    action['approach'],
                    context={}
                )
                
                return {
                    'action': action,
                    'suggestions': suggestions,
                    'lead_update': result['extracted_data']
                }
        
        return {'action': {'action': 'wait'}, 'suggestions': []}
    
    def check_follow_ups(self):
        """Check all active leads for follow-up needs"""
        active_leads = self.memory.get_active_leads(hours=72)
        follow_ups = []
        
        for lead in active_leads:
            action = self.strategist.decide_action(
                lead,
                last_message_from_customer=False,
                conversation_history=[]
            )
            
            if action['action'] == 'follow_up':
                suggestions = self.closer.generate_suggestions(
                    lead,
                    action['approach'],
                    context={}
                )
                
                follow_ups.append({
                    'lead': lead,
                    'suggestions': suggestions
                })
        
        return follow_ups

# Example usage
if __name__ == "__main__":
    broker = ZaloAIBroker()
    
    # Simulate conversation
    result = broker.process_conversation(
        lead_id="lead_001",
        new_message="Chào em, anh muốn tìm căn hộ 2PN ở Quận 2, tầm 2-3 tỷ, có view sông không em?"
    )
    
    print("Action:", result['action'])
    print("\nSuggestions:")
    for i, suggestion in enumerate(result['suggestions'], 1):
        print(f"\n{i}. {suggestion.message}")
        print(f"   Tactics: {', '.join(suggestion.tactics)}")
        print(f"   Confidence: {suggestion.confidence:.2f}")
```

### Requirements.txt
```
fastapi==0.104.1
uvicorn==0.24.0
redis==5.0.1
underthesea==6.7.0
pydantic==2.5.0
python-multipart==0.0.6
```

### Docker Setup (Dockerfile)
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install Vietnamese language support
RUN apt-get update && apt-get install -y \
    locales \
    && echo "vi_VN.UTF-8 UTF-8" > /etc/locale.gen \
    && locale-gen

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV LANG=vi_VN.UTF-8
ENV LC_ALL=vi_VN.UTF-8

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Testing Strategy

### Unit Tests (test_extraction.py)
```python
def test_budget_extraction():
    extractor = VietnameseExtractor()
    
    test_cases = [
        ("tầm 2-3 tỷ", (2_000_000_000, 3_000_000_000)),
        ("khoảng 2.5 tỷ", (2_125_000_000, 2_875_000_000)),
        ("500 triệu", (425_000_000, 575_000_000))
    ]
    
    for text, expected in test_cases:
        result = extractor.extract_budget(text)
        assert result == expected

def test_interest_classification():
    extractor = VietnameseExtractor()
    
    assert extractor.classify_interest("cần gấp trong tuần") == InterestLevel.HOT
    assert extractor.classify_interest("đang tìm hiểu") == InterestLevel.WARM
    assert extractor.classify_interest("chỉ xem thôi") == InterestLevel.COLD
```

## Performance Optimizations

1. **Caching**: Cache extracted lead data for 5 minutes
2. **Batch Processing**: Process follow-ups in batches
3. **Template Preloading**: Load all templates on startup
4. **Connection Pooling**: Reuse Redis connections

## Deployment Commands

```bash
# Development
python main.py

# Production with Gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker

# Docker
docker build -t zalo-ai-broker .
docker run -p 8000:8000 -v $(pwd)/data:/app/data zalo-ai-broker
```

This implementation provides a working MVP that can be built in 6 days with clear daily milestones.