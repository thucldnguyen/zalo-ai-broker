"""
Zalo webhook routes for FastAPI

Handles incoming messages from Zalo and sends AI suggestions back
"""

from fastapi import APIRouter, Request, HTTPException, Header, Depends
from typing import Optional
import os

from integrations.zalo_client import ZaloClient, ZaloAuthManager
from core.memory import LeadStore, ConversationHistory
from core.models import LeadProfile


router = APIRouter(prefix="/zalo", tags=["zalo"])

auth_manager = ZaloAuthManager()


def get_lead_store() -> LeadStore:
    return LeadStore()


def get_conv_history() -> ConversationHistory:
    return ConversationHistory()


def get_app_credentials() -> dict:
    app_id = os.getenv("ZALO_APP_ID")
    app_secret = os.getenv("ZALO_APP_SECRET")
    if not app_id or not app_secret:
        raise HTTPException(status_code=500, detail="Zalo credentials not configured")
    return {"app_id": app_id, "app_secret": app_secret}


# Zalo auth manager for multi-user support
auth_manager = ZaloAuthManager()


@router.post("/webhook")
async def zalo_webhook(
    request: Request,
    x_zalo_signature: Optional[str] = Header(None),
    x_zalo_timestamp: Optional[str] = Header(None),
    creds: dict = Depends(get_app_credentials),
    lead_store: LeadStore = Depends(get_lead_store),
    conv_history: ConversationHistory = Depends(get_conv_history),
):
    """
    Receive messages from Zalo webhook

    Zalo will POST here when users send messages
    """
    app_id = creds["app_id"]
    app_secret = creds["app_secret"]

    body = await request.body()
    payload = await request.json()

    client = ZaloClient(app_id, app_secret)
    if x_zalo_signature and x_zalo_timestamp:
        if not client.verify_webhook(x_zalo_signature, x_zalo_timestamp, body.decode()):
            raise HTTPException(status_code=401, detail="Invalid signature")

    message_data = ZaloClient.parse_webhook_message(payload)
    if not message_data:
        return {"status": "ignored", "reason": "not_a_text_message"}

    user_id = message_data["user_id"]
    text = message_data["text"]

    broker_id = os.getenv("DEFAULT_BROKER_ID", "default_broker")
    broker_client = auth_manager.get_client_for_broker(broker_id, app_id, app_secret)
    if not broker_client:
        return {"status": "error", "reason": "broker_not_authenticated"}

    from agents.listener import ListenerAgent
    from agents.strategist import StrategistAgent
    from agents.closer import CloserAgent
    from core.llm.provider import AnthropicLLMProvider

    api_key = os.getenv("ANTHROPIC_API_KEY")
    llm_provider = AnthropicLLMProvider(api_key=api_key) if api_key else None

    listener_agent = ListenerAgent(lead_store, conv_history, llm_provider=llm_provider)
    strategist_agent = StrategistAgent(lead_store, conv_history)
    closer_agent = CloserAgent(llm_provider=llm_provider)

    lead_id = f"zalo_{user_id}"

    listener_result = await listener_agent.process_message(
        message_text=text,
        lead_id=lead_id,
        is_broker=False,
    )

    profile = listener_result["profile"]

    action = strategist_agent.decide_action(lead_id)

    suggestions = []
    if action["action"] in ["quick_reply", "follow_up", "gentle_nudge"]:
        approach = action.get("suggested_approach", "value_proposition")
        recent_history = conv_history.get_history(lead_id, limit=6)

        suggestions_obj = await closer_agent.generate_suggestions(
            profile=profile,
            approach=approach,
            context=text,
            count=3,
            history=recent_history,
        )
        suggestions = [s.message for s in suggestions_obj]

    if suggestions:
        best_suggestion = suggestions[0]
        await broker_client.send_message(user_id, best_suggestion)

    return {
        "status": "success",
        "lead_id": lead_id,
        "action": action["action"],
        "suggestion_sent": len(suggestions) > 0,
    }


@router.get("/webhook")
async def zalo_webhook_verify(
    hub_mode: Optional[str] = None,
    hub_challenge: Optional[str] = None,
    hub_verify_token: Optional[str] = None,
):
    """
    Webhook verification endpoint

    Zalo will call this to verify your webhook URL
    """
    verify_token = os.getenv("ZALO_VERIFY_TOKEN", "your_verify_token_here")

    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        if hub_challenge:
            return int(hub_challenge)

    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/send")
async def send_message_to_lead(
    lead_id: str,
    message: str,
    broker_id: str = "default_broker",
    creds: dict = Depends(get_app_credentials),
):
    """
    Send a message to a lead via Zalo

    Used when broker manually wants to send a message
    """
    app_id = creds["app_id"]
    app_secret = creds["app_secret"]

    broker_client = auth_manager.get_client_for_broker(broker_id, app_id, app_secret)
    if not broker_client:
        raise HTTPException(status_code=401, detail="Broker not authenticated")

    if lead_id.startswith("zalo_"):
        zalo_user_id = lead_id[5:]
    else:
        raise HTTPException(status_code=400, detail="Invalid lead_id format")

    result = await broker_client.send_message(zalo_user_id, message)

    return {"status": "sent", "zalo_response": result}


@router.post("/auth/save-token")
async def save_broker_token(broker_id: str, access_token: str, refresh_token: str):
    """
    Save OAuth tokens for a broker

    After broker completes OAuth flow, save their tokens here
    """
    auth_manager.save_token(broker_id, access_token, refresh_token)

    return {
        "status": "success",
        "broker_id": broker_id,
        "message": "Tokens saved successfully",
    }
