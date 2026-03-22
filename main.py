"""
Zalo AI Broker Assistant - Main Application

FastAPI application that coordinates all three agents:
- Listener: Extracts data from messages
- Strategist: Decides actions
- Closer: Generates reply suggestions

Usage:
    uvicorn main:app --reload
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from core.models import LeadProfile, Suggestion
from core.memory import LeadStore, ConversationHistory
from agents.listener import ListenerAgent
from agents.strategist import StrategistAgent
from agents.closer import CloserAgent


# Initialize app
app = FastAPI(
    title="Zalo AI Broker Assistant",
    description="AI-powered assistant for Vietnamese real estate brokers",
    version="0.1.0"
)

# Initialize storage
lead_store = LeadStore()
conv_history = ConversationHistory()

# Initialize agents
listener = ListenerAgent(lead_store, conv_history)
strategist = StrategistAgent(lead_store, conv_history)
closer = CloserAgent()


# Request/Response models
class MessageRequest(BaseModel):
    """Incoming message from Zalo"""
    lead_id: str
    message: str
    is_broker: bool = False
    response_time_seconds: Optional[int] = None


class ProcessResponse(BaseModel):
    """Response with suggestions and analysis"""
    profile: dict
    extracted_data: dict
    action: dict
    suggestions: List[dict]
    is_new_lead: bool


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "app": "Zalo AI Broker Assistant",
        "version": "0.1.0",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/process", response_model=ProcessResponse)
async def process_message(request: MessageRequest):
    """
    Process an incoming message through all agents
    
    Flow:
    1. Listener extracts data and updates lead profile
    2. Strategist decides what action to take
    3. Closer generates reply suggestions
    
    Returns complete analysis and suggestions
    """
    try:
        # Step 1: Listener processes message
        listener_result = listener.process_message(
            message_text=request.message,
            lead_id=request.lead_id,
            is_broker=request.is_broker,
            response_time_seconds=request.response_time_seconds
        )
        
        # Skip agent processing for broker messages
        if listener_result.get('extraction_skipped'):
            return JSONResponse(
                status_code=200,
                content={
                    "message": "Broker message saved",
                    "profile": None,
                    "extracted_data": None,
                    "action": None,
                    "suggestions": [],
                    "is_new_lead": False
                }
            )
        
        profile = listener_result['profile']
        
        # Step 2: Strategist decides action
        action = strategist.decide_action(request.lead_id)
        
        # Step 3: Closer generates suggestions (if action requires it)
        suggestions = []
        if action['action'] in ['quick_reply', 'follow_up', 'gentle_nudge']:
            approach = action.get('suggested_approach', 'value_proposition')
            context = request.message if action['action'] == 'quick_reply' else None
            
            suggestions_obj = closer.generate_suggestions(
                profile=profile,
                approach=approach,
                context=context,
                count=3
            )
            suggestions = [s.to_dict() for s in suggestions_obj]
        
        return {
            "profile": profile.to_dict(),
            "extracted_data": listener_result['extracted_data'],
            "action": action,
            "suggestions": suggestions,
            "is_new_lead": listener_result['is_new_lead']
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/lead/{lead_id}")
async def get_lead(lead_id: str):
    """Get lead profile and recent conversation"""
    summary = listener.get_lead_summary(lead_id)
    
    if not summary:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return {
        "profile": summary['profile'].to_dict(),
        "recent_messages": [m.to_dict() for m in summary['recent_messages']],
        "message_count": summary['message_count']
    }


@app.get("/leads/hot")
async def get_hot_leads():
    """Get all hot leads"""
    hot_leads = lead_store.get_hot_leads()
    return {
        "count": len(hot_leads),
        "leads": [lead.to_dict() for lead in hot_leads]
    }


@app.get("/follow-ups")
async def get_follow_ups(hours: int = 24):
    """Get all follow-up tasks in the next N hours"""
    tasks = strategist.get_follow_up_tasks(cutoff_hours=hours)
    return {
        "count": len(tasks),
        "tasks": [task.to_dict() for task in tasks]
    }


@app.get("/stats")
async def get_stats():
    """Get storage statistics"""
    return lead_store.get_stats()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
