# Zalo AI Broker Assistant

AI-powered assistant for Vietnamese real estate brokers to close more deals.

## Problem

Vietnamese real estate brokers lose deals due to:
- Slow reply times (30+ minutes average)
- Poor follow-up discipline (40% follow-up rate)
- Generic, unpersuasive messaging

## Solution

Multi-agent AI system that:
1. **Understands** Vietnamese real estate conversations
2. **Decides** when and how to follow up
3. **Generates** persuasive, personalized reply suggestions

## Architecture

```
Customer Message → Listener Agent → Extract Info
                         ↓
                  Strategist Agent → Decide Action  
                         ↓
                   Closer Agent → Generate Replies
                         ↓
                Broker Reviews & Sends
```

### Agents

**Listener Agent**
- Extracts: budget, location, intent, interest level
- Updates lead profiles
- Stores conversation history

**Strategist Agent**  
- Decides: quick reply, follow-up, or wait
- Timing rules: hot (2h), warm (24h), cold (72h)
- Prioritizes high-value leads

**Closer Agent**
- Generates 3 Vietnamese reply options
- Tactics: urgency, scarcity, social proof, value proposition
- Confidence scoring

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/thucldnguyen/zalo-ai-broker.git
cd zalo-ai-broker

# Install dependencies
pip install -r requirements.txt
```

### Run the API

```bash
# Start FastAPI server
uvicorn main:app --reload

# Server runs at http://localhost:8000
```

### Try the Demo

```bash
# In another terminal
python example_usage.py
```

This will simulate a conversation and show:
- Extracted data from Vietnamese text
- AI-generated reply suggestions
- Follow-up recommendations

## API Usage

### Process a Message

```bash
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{
    "lead_id": "customer_001",
    "message": "Chào em, anh muốn tìm căn hộ 2PN ở Quận 2, tầm 2-3 tỷ",
    "is_broker": false
  }'
```

**Response:**
```json
{
  "profile": {
    "lead_id": "customer_001",
    "budget_min": 1700000000,
    "budget_max": 3450000000,
    "locations": ["quận 2"],
    "intent": "buy",
    "interest_level": "warm"
  },
  "action": {
    "action": "quick_reply",
    "priority": "high",
    "reasoning": "Customer asked a question - respond quickly"
  },
  "suggestions": [
    {
      "message": "Dạ anh, em đang có 3 căn 2PN view sông tuyệt đẹp ở Q2...",
      "tactics": ["value_proposition"],
      "confidence": 0.85
    }
  ]
}
```

### Get Hot Leads

```bash
curl http://localhost:8000/leads/hot
```

### Get Follow-up Tasks

```bash
curl http://localhost:8000/follow-ups?hours=24
```

### Get Lead Details

```bash
curl http://localhost:8000/lead/customer_001
```

## Vietnamese NLP Features

### LLM-Powered Intelligence (Optional)

When `ANTHROPIC_API_KEY` is configured, the system uses Claude for:
- **Smarter extraction**: Better handling of complex Vietnamese phrasing
- **Contextual replies**: Personalized suggestions based on conversation history
- **Graceful fallback**: Automatically uses rule-based heuristics if LLM unavailable

Set `ANTHROPIC_API_KEY` in `.env` to enable (see `.env.example`).

### Budget Extraction
- "tầm 2-3 tỷ" → 2,000,000,000 - 3,000,000,000 VND
- "khoảng 500 triệu" → 425,000,000 - 575,000,000 VND

### Location Detection
- Districts: Quận 2, Q2, Thủ Đức, etc.
- Areas: Thảo Điền, An Phú, Sala, etc.
- Projects: Vinhomes, Masteri, Gateway, etc.

### Interest Level Classification
- **HOT**: "cần gấp", "trong tuần", quick responses
- **WARM**: "đang tìm", "quan tâm", asks questions
- **COLD**: Just browsing, slow responses

### Intent Detection
- BUY: "mua", "sở hữu", "về ở"
- INVEST: "đầu tư", "cho thuê", "sinh lời"  
- RENT: "thuê", "cần thuê"

## Message Templates

Closer agent uses these persuasion tactics:

- **Urgency**: "Căn này đang có 2 khách khác quan tâm..."
- **Scarcity**: "Chỉ còn 3 căn trong tầm giá của anh..."
- **Social Proof**: "Tuần trước em bán 5 căn cùng khu..."
- **Value**: "Với budget 2 tỷ, đây là căn đáng giá nhất..."
- **Limited Time**: "Chủ nhà giảm thêm 50tr nếu quyết định trong tuần..."

## Data Storage

**MVP**: JSON files
- Leads: `data/leads/{lead_id}.json`
- Conversations: `data/conversations/{lead_id}.jsonl`
- Index: `data/leads/index.json`

**Future**: Migrate to PostgreSQL with JSONB

## Project Structure

```
zalo-ai-broker/
├── agents/
│   ├── listener.py       # Data extraction
│   ├── strategist.py     # Action decisions
│   └── closer.py         # Message generation
├── core/
│   ├── models.py         # Data models
│   ├── vietnamese_nlp.py # Vietnamese processing
│   └── memory.py         # Storage layer
├── data/
│   ├── leads/            # Lead profiles (JSON)
│   └── conversations/    # Message history (JSONL)
├── templates/
│   └── messages.json     # Message templates
├── tests/
├── main.py               # FastAPI application
├── example_usage.py      # Demo script
└── requirements.txt
```

## Development Roadmap

### ✅ Phase 1: MVP (Week 1)
- Core data models
- Vietnamese NLP extraction
- Three agents (Listener, Strategist, Closer)
- JSON storage
- FastAPI endpoints

### 🔄 Phase 2: Integration (Week 2-3)
- [ ] Zalo API integration
- [ ] Real-time webhook processing
- [ ] Broker feedback loop
- [ ] A/B testing framework

### 📊 Phase 3: Enhancement (Week 4+)
- [ ] PostgreSQL migration
- [ ] Advanced NLP (ML models)
- [ ] Multi-broker support
- [ ] Analytics dashboard

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Reply Time | 30+ min | < 5 min |
| Follow-up Rate | 40% | 95% |
| Message Quality | Generic | Personalized |
| Lead Conversion | Baseline | +30% |

## Contributing

This is a production project for real estate brokers. Contributions welcome!

## License

MIT License - see LICENSE file

## Credits

Architecture designed by Tech Lead agent (@ThucTechLead_bot)  
Implementation by Clawy 🦀

Built with Claude Sonnet 4.5 via ClawForce orchestration platform.
