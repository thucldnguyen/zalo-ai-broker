"""
Zalo webhook routes for FastAPI

Handles incoming messages from Zalo and sends AI suggestions back
"""

from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional
import os

from integrations.zalo_client import ZaloClient, ZaloAuthManager
from agents.listener import ListenerAgent
from agents.strategist import StrategistAgent
from agents.closer import CloserAgent


router = APIRouter(prefix="/zalo", tags=["zalo"])

# Zalo auth manager for multi-user support
auth_manager = ZaloAuthManager()


@router.post("/webhook")
async def zalo_webhook(
    request: Request,
    x_zalo_signature: Optional[str] = Header(None),
    x_zalo_timestamp: Optional[str] = Header(None)
):
    """
    Receive messages from Zalo webhook
    
    Zalo will POST here when users send messages
    """
    # Get app credentials from environment
    app_id = os.getenv('ZALO_APP_ID')
    app_secret = os.getenv('ZALO_APP_SECRET')
    
    if not app_id or not app_secret:
        raise HTTPException(status_code=500, detail="Zalo credentials not configured")
    
    # Get request body
    body = await request.body()
    payload = await request.json()
    
    # Verify webhook signature
    client = ZaloClient(app_id, app_secret)
    if x_zalo_signature and x_zalo_timestamp:
        if not client.verify_webhook(x_zalo_signature, x_zalo_timestamp, body.decode()):
            raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse message
    message_data = ZaloClient.parse_webhook_message(payload)
    if not message_data:
        return {"status": "ignored", "reason": "not_a_text_message"}
    
    user_id = message_data['user_id']
    text = message_data['text']
    
    # TODO: Map Zalo user_id to broker_id
    # For now, use a default broker or get from context
    broker_id = os.getenv('DEFAULT_BROKER_ID', 'default_broker')
    
    # Get authenticated client for this broker
    broker_client = auth_manager.get_client_for_broker(broker_id, app_id, app_secret)
    if not broker_client:
        return {"status": "error", "reason": "broker_not_authenticated"}
    
    # Process message through agents (imported from main app)
    from main import listener, strategist, closer
    
    # Use Zalo user_id as lead_id
    lead_id = f"zalo_{user_id}"
    
    # Step 1: Listener processes message
    listener_result = listener.process_message(
        message_text=text,
        lead_id=lead_id,
        is_broker=False
    )
    
    profile = listener_result['profile']
    
    # Step 2: Strategist decides action
    action = strategist.decide_action(lead_id)
    
    # Step 3: Closer generates suggestions
    suggestions = []
    if action['action'] in ['quick_reply', 'follow_up', 'gentle_nudge']:
        approach = action.get('suggested_approach', 'value_proposition')
        
        suggestions_obj = closer.generate_suggestions(
            profile=profile,
            approach=approach,
            context=text,
            count=3
        )
        suggestions = [s.message for s in suggestions_obj]
    
    # Send first suggestion automatically (or wait for broker approval)
    # For MVP, let's send it automatically
    if suggestions:
        best_suggestion = suggestions[0]
        broker_client.send_message(user_id, best_suggestion)
    
    return {
        "status": "success",
        "lead_id": lead_id,
        "action": action['action'],
        "suggestion_sent": len(suggestions) > 0
    }


@router.get("/webhook")
async def zalo_webhook_verify(
    hub_mode: str = None,
    hub_challenge: str = None,
    hub_verify_token: str = None
):
    """
    Webhook verification endpoint
    
    Zalo will call this to verify your webhook URL
    """
    verify_token = os.getenv('ZALO_VERIFY_TOKEN', 'your_verify_token_here')
    
    if hub_mode == 'subscribe' and hub_verify_token == verify_token:
        return int(hub_challenge)
    
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/send")
async def send_message_to_lead(
    lead_id: str,
    message: str,
    broker_id: str = "default_broker"
):
    """
    Send a message to a lead via Zalo
    
    Used when broker manually wants to send a message
    """
    app_id = os.getenv('ZALO_APP_ID')
    app_secret = os.getenv('ZALO_APP_SECRET')
    
    if not app_id or not app_secret:
        raise HTTPException(status_code=500, detail="Zalo credentials not configured")
    
    # Get broker's Zalo client
    broker_client = auth_manager.get_client_for_broker(broker_id, app_id, app_secret)
    if not broker_client:
        raise HTTPException(status_code=401, detail="Broker not authenticated")
    
    # Extract Zalo user_id from lead_id
    if lead_id.startswith('zalo_'):
        zalo_user_id = lead_id[5:]  # Remove 'zalo_' prefix
    else:
        raise HTTPException(status_code=400, detail="Invalid lead_id format")
    
    # Send message
    result = broker_client.send_message(zalo_user_id, message)
    
    return {
        "status": "sent",
        "zalo_response": result
    }


@router.post("/auth/save-token")
async def save_broker_token(
    broker_id: str,
    access_token: str,
    refresh_token: str
):
    """
    Save OAuth tokens for a broker
    
    After broker completes OAuth flow, save their tokens here
    """
    auth_manager.save_token(broker_id, access_token, refresh_token)
    
    return {
        "status": "success",
        "broker_id": broker_id,
        "message": "Tokens saved successfully"
    }
