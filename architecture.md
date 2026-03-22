# Zalo AI Assistant for Real Estate Brokers - Architecture Design

## Executive Summary

We're building an AI assistant that helps Vietnamese real estate brokers close more deals by solving their core problems: slow replies, poor follow-up timing, and weak persuasive messaging. The system uses a multi-agent architecture to understand conversations, suggest high-converting replies in Vietnamese, and proactively recommend follow-ups. MVP focuses on three capabilities: conversation understanding, reply generation, and follow-up decisions.

## 1. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Input Layer                           │
├─────────────────────────────────────────────────────────────┤
│  Zalo Conversation (Text) → Message Queue → Parser          │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                      Agent Layer                             │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐       │
│  │  Listener   │  │  Strategist  │  │   Closer    │       │
│  │   Agent     │◄─┤    Agent     ├─►│   Agent     │       │
│  └──────┬──────┘  └──────┬───────┘  └──────┬──────┘       │
│         │                 │                  │               │
│         ▼                 ▼                  ▼               │
│  ┌──────────────────────────────────────────────┐          │
│  │           Shared Memory (Lead Store)          │          │
│  └──────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                      Output Layer                            │
├─────────────────────────────────────────────────────────────┤
│  Reply Suggestions │ Follow-up Tasks │ Lead Updates         │
└─────────────────────────────────────────────────────────────┘
```

## 2. Agent Definitions

### 2.1 Listener Agent
**Purpose**: Parse incoming messages and extract structured information

**Input**:
- Raw Zalo conversation text
- Lead ID (if existing conversation)

**Processing**:
```python
# Core extraction logic
- Detect customer name using Vietnamese name patterns
- Extract budget using regex: "tầm 2-3 tỷ", "khoảng 1.5 tỷ"
- Identify location mentions: districts, streets, projects
- Classify intent: mua (buy), đầu tư (invest), thuê (rent)
- Score interest level based on keywords and engagement
```

**Output**:
```json
{
  "lead_id": "lead_123",
  "extracted_data": {
    "customer_name": "Anh Minh",
    "budget_range": {"min": 2000000000, "max": 3000000000},
    "locations": ["Quận 2", "Thủ Đức"],
    "intent": "buy",
    "interest_level": "hot",
    "key_phrases": ["cần gấp", "trong tháng này"]
  },
  "timestamp": "2024-03-22T10:30:00Z"
}
```

### 2.2 Strategist Agent
**Purpose**: Decide next best action based on lead state and context

**Input**:
- Current lead state from memory
- Latest interaction data
- Time since last contact

**Decision Logic**:
```python
# Rules-based with ML enhancement
if interest_level == "hot" and hours_since_contact > 2:
    action = "immediate_follow_up"
elif interest_level == "warm" and days_since_contact > 1:
    action = "gentle_follow_up"
elif customer_asked_question:
    action = "quick_reply"
else:
    action = "wait"
```

**Output**:
```json
{
  "action": "quick_reply",
  "priority": "high",
  "reasoning": "Customer asked about payment terms - high intent signal",
  "suggested_approach": "address_concern_with_urgency"
}
```

### 2.3 Closer Agent
**Purpose**: Generate persuasive Vietnamese messages

**Input**:
- Conversation history
- Lead profile
- Strategic approach from Strategist

**Message Generation**:
```python
# Templates with dynamic insertion
templates = {
    "urgency": "Anh {name} ơi, căn này đang có 2 khách khác quan tâm. Em sợ lỡ mất cơ hội tốt cho anh.",
    "social_proof": "Tuần trước em vừa bán 3 căn cùng khu cho khách đầu tư. Giá đang tăng đều {percent}%/năm.",
    "objection_handling": "Em hiểu anh lo về {concern}. Thực tế {counterpoint}. Nhiều khách của em ban đầu cũng lo vậy."
}
```

**Output**:
```json
{
  "suggestions": [
    {
      "message": "Anh Minh ơi, căn 2PN view sông em vừa gửi đang có 2 khách khác quan tâm. Em sợ lỡ mất cơ hội tốt cho anh. Anh có muốn em giữ lại để mình xem thứ 7 không ạ?",
      "tactics": ["urgency", "scarcity"],
      "confidence": 0.85
    },
    {
      "message": "Chào anh Minh, em vừa check với chủ nhà, họ đồng ý giảm thêm 50tr nếu anh quyết định trong tuần này. Cơ hội này hiếm lắm anh ạ!",
      "tactics": ["limited_time_offer", "negotiation"],
      "confidence": 0.78
    }
  ]
}
```

## 3. Memory Schema

### 3.1 Lead Profile Storage
```json
{
  "lead_id": "lead_123",
  "profile": {
    "name": "Nguyễn Văn Minh",
    "phone": "0901234567",
    "preferences": {
      "budget_min": 2000000000,
      "budget_max": 3000000000,
      "locations": ["Quận 2", "Thủ Đức", "Bình Thạnh"],
      "property_types": ["apartment", "villa"],
      "intent": "buy",
      "timeline": "within_3_months"
    },
    "behavioral_insights": {
      "response_time_preference": "morning",
      "communication_style": "formal",
      "decision_factors": ["location", "price", "investment_potential"]
    }
  },
  "interaction_history": [
    {
      "timestamp": "2024-03-22T10:30:00Z",
      "type": "inquiry",
      "message": "Anh muốn tìm căn hộ 2PN ở Quận 2",
      "broker_response": "Dạ em có nhiều căn phù hợp...",
      "outcome": "interested"
    }
  ],
  "metrics": {
    "interest_level": "hot",
    "last_contact": "2024-03-22T10:30:00Z",
    "total_interactions": 5,
    "response_rate": 0.8
  }
}
```

### 3.2 Storage Implementation
- **MVP**: JSON files in `data/leads/` directory
- **Future**: PostgreSQL with JSONB for flexible schema
- **Indexing**: By lead_id, phone number, last_contact

## 4. Example Flow

### Input Conversation:
```
Customer: Chào em, anh muốn tìm căn hộ 2PN ở Quận 2, tầm 2-3 tỷ
Broker: Dạ chào anh, em có nhiều căn phù hợp với anh. Anh cần gấp không ạ?
Customer: Anh đang tìm hiểu thôi, có căn nào view sông không em?
```

### Agent Processing:

**Step 1 - Listener Agent**:
- Extracts: budget (2-3B), location (Q2), type (2PN), feature (river view)
- Interest level: "warm" (browsing, not urgent)

**Step 2 - Strategist Agent**:
- Decision: "quick_reply" with "feature_highlight" approach
- Reasoning: Customer showed specific preference (river view)

**Step 3 - Closer Agent**:
Generates suggestions:
1. "Dạ anh, em đang có 2 căn 2PN view sông tuyệt đẹp ở Q2. Một căn tầng 15 giá 2.8 tỷ, một căn tầng 20 giá 3.2 tỷ. Anh muốn em gửi hình không ạ? 📸"

2. "Anh ơi, căn view sông ở Q2 hiện đang rất hot. Tuần trước em vừa bán 1 căn tương tự. Em gửi anh xem căn đẹp nhất trong tầm giá của anh nhé!"

### Follow-up Decision:
- If no response in 4 hours → Send follow-up
- Message: "Anh Minh ơi, em vừa gửi thông tin 2 căn view sông. Anh xem có ưng ý căn nào không ạ? Chiều nay em có thể sắp xếp cho anh xem luôn."

## 5. MVP Implementation Plan (6 Days)

### Day 1-2: Core Infrastructure
- Set up Python project structure
- Implement JSON-based lead storage
- Create message queue simulator
- Basic logging and monitoring

### Day 3: Listener Agent
- Vietnamese text processing utilities
- Budget/location extraction regex
- Intent classification rules
- Interest scoring algorithm

### Day 4: Strategist Agent
- Decision tree implementation
- Time-based follow-up rules
- Priority scoring system
- Action recommendation engine

### Day 5: Closer Agent
- Vietnamese message templates
- Dynamic content insertion
- Persuasion tactic selection
- A/B test framework prep

### Day 6: Integration & Testing
- Agent communication protocol
- End-to-end flow testing
- Vietnamese language validation
- Performance optimization

## 6. Technical Stack

### Core:
- **Language**: Python 3.11
- **Framework**: FastAPI for API layer
- **Queue**: Redis for message passing
- **Storage**: JSON files → PostgreSQL
- **NLP**: Underthesea for Vietnamese

### Agent Framework:
- **Base**: OpenClaw agent system
- **Memory**: Shared JSON store
- **Communication**: Redis pub/sub

### Deployment:
- **MVP**: Single Docker container
- **Production**: Kubernetes with agent scaling

## 7. Agentic Behavior Implementation

### Proactive Actions:
```python
# Scheduled job every 30 minutes
def check_follow_ups():
    for lead in get_active_leads():
        if should_follow_up(lead):
            strategist.create_follow_up_task(lead)
```

### Adaptive Learning:
```python
# Track message effectiveness
def update_lead_model(lead_id, response):
    if response.replied_quickly:
        increase_tactic_score("urgency")
    if response.asked_for_viewing:
        mark_as_hot_lead()
```

### Decision Boundaries:
- Max 2 follow-ups per day per lead
- Wait 4+ hours between messages
- Escalate to human if 3 messages ignored

## 8. Evolution Path

### Phase 2: Zalo Integration
- Official Zalo API integration
- Real-time message webhooks
- Automated response sending

### Phase 3: Multi-Broker Platform
- Broker accounts & permissions
- Team lead dashboards
- Performance analytics

### Phase 4: Monetization
- Subscription tiers (Basic/Pro/Enterprise)
- Pay-per-closed-deal model
- Training & certification program

## 9. Success Metrics

### MVP Metrics:
- Message suggestion acceptance rate > 60%
- Follow-up timing accuracy > 80%
- Lead interest classification accuracy > 75%

### Business Metrics:
- Response time: < 5 minutes → < 1 minute
- Follow-up rate: 40% → 95%
- Lead-to-viewing conversion: +30%

## 10. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Poor Vietnamese NLP | Use rule-based extraction + human validation |
| Over-messaging | Hard limits + broker override controls |
| Generic responses | A/B test templates, collect broker feedback |
| Zalo API changes | Abstract integration layer, multiple fallbacks |

---

This architecture prioritizes shipping speed while maintaining quality. The modular agent design allows independent development and testing. Focus on the core value prop: help brokers close more deals through better follow-up and messaging.