"""
Zalo API Client for Official Account integration

Handles:
- Receiving messages via webhook
- Sending messages to users
- OAuth authentication
- Multi-user support
"""

import os
import hmac
import hashlib
import requests
from typing import Dict, Any, Optional
from datetime import datetime


class ZaloClient:
    """
    Client for Zalo Official Account API
    
    Setup:
    1. Create Zalo Official Account at https://oa.zalo.me/
    2. Get App ID, App Secret from Zalo Developer Portal
    3. Set webhook URL in Zalo dashboard
    """
    
    API_BASE = "https://openapi.zalo.me/v2.0/oa"
    
    def __init__(self, app_id: str, app_secret: str, access_token: Optional[str] = None):
        """
        Initialize Zalo client
        
        Args:
            app_id: Zalo App ID
            app_secret: Zalo App Secret  
            access_token: OAuth access token (optional, can refresh)
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.access_token = access_token
    
    def verify_webhook(self, signature: str, timestamp: str, body: str) -> bool:
        """
        Verify webhook request is from Zalo
        
        Args:
            signature: X-Zalo-Signature header
            timestamp: X-Zalo-Timestamp header
            body: Request body string
        
        Returns:
            True if signature is valid
        """
        message = f"{timestamp}{body}"
        expected_sig = hmac.new(
            self.app_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_sig)
    
    def send_message(self, recipient_id: str, message: str) -> Dict[str, Any]:
        """
        Send text message to user
        
        Args:
            recipient_id: Zalo user ID
            message: Message text
        
        Returns:
            API response dict
        """
        if not self.access_token:
            raise ValueError("Access token required. Please authenticate first.")
        
        url = f"{self.API_BASE}/message"
        headers = {
            "access_token": self.access_token,
            "Content-Type": "application/json"
        }
        
        payload = {
            "recipient": {
                "user_id": recipient_id
            },
            "message": {
                "text": message
            }
        }
        
        response = requests.post(url, json=payload, headers=headers)
        return response.json()
    
    def send_suggestions(
        self, 
        recipient_id: str, 
        text: str, 
        suggestions: list
    ) -> Dict[str, Any]:
        """
        Send message with quick reply suggestions
        
        Args:
            recipient_id: Zalo user ID
            text: Message text
            suggestions: List of suggestion texts
        
        Returns:
            API response dict
        """
        if not self.access_token:
            raise ValueError("Access token required")
        
        url = f"{self.API_BASE}/message"
        headers = {
            "access_token": self.access_token,
            "Content-Type": "application/json"
        }
        
        # Format suggestions as quick replies
        quick_replies = [
            {"content_type": "text", "title": s[:20], "payload": s}
            for s in suggestions[:3]  # Max 3 quick replies
        ]
        
        payload = {
            "recipient": {
                "user_id": recipient_id
            },
            "message": {
                "text": text,
                "quick_replies": quick_replies
            }
        }
        
        response = requests.post(url, json=payload, headers=headers)
        return response.json()
    
    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Get user profile information
        
        Args:
            user_id: Zalo user ID
        
        Returns:
            User profile dict
        """
        if not self.access_token:
            raise ValueError("Access token required")
        
        url = f"{self.API_BASE}/getuser"
        params = {
            "access_token": self.access_token,
            "data": {
                "user_id": user_id
            }
        }
        
        response = requests.get(url, params=params)
        return response.json()
    
    @staticmethod
    def parse_webhook_message(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse incoming webhook message
        
        Args:
            payload: Webhook POST body
        
        Returns:
            Parsed message dict with user_id, text, timestamp
        """
        try:
            event = payload.get('event')
            if not event or event != 'user_send_text':
                return None
            
            return {
                'user_id': payload.get('sender', {}).get('id'),
                'text': payload.get('message', {}).get('text'),
                'timestamp': payload.get('timestamp'),
                'message_id': payload.get('message', {}).get('msg_id')
            }
        except Exception as e:
            print(f"Error parsing webhook: {e}")
            return None


class ZaloAuthManager:
    """
    Manage OAuth tokens for multiple Zalo accounts
    
    Each broker gets their own access token
    """
    
    def __init__(self, tokens_file: str = "data/zalo_tokens.json"):
        """
        Initialize auth manager
        
        Args:
            tokens_file: Path to JSON file storing tokens
        """
        self.tokens_file = tokens_file
        self._ensure_tokens_file()
    
    def _ensure_tokens_file(self):
        """Create tokens file if it doesn't exist"""
        import json
        from pathlib import Path
        
        path = Path(self.tokens_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        if not path.exists():
            path.write_text(json.dumps({}))
    
    def save_token(self, broker_id: str, access_token: str, refresh_token: str):
        """Save OAuth tokens for a broker"""
        import json
        from pathlib import Path
        
        tokens = json.loads(Path(self.tokens_file).read_text())
        tokens[broker_id] = {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'updated_at': datetime.now().isoformat()
        }
        Path(self.tokens_file).write_text(json.dumps(tokens, indent=2))
    
    def get_token(self, broker_id: str) -> Optional[str]:
        """Get access token for a broker"""
        import json
        from pathlib import Path
        
        tokens = json.loads(Path(self.tokens_file).read_text())
        broker_tokens = tokens.get(broker_id)
        
        if broker_tokens:
            return broker_tokens['access_token']
        
        return None
    
    def get_client_for_broker(
        self, 
        broker_id: str, 
        app_id: str, 
        app_secret: str
    ) -> Optional[ZaloClient]:
        """
        Get authenticated Zalo client for a broker
        
        Args:
            broker_id: Broker identifier
            app_id: Zalo App ID
            app_secret: Zalo App Secret
        
        Returns:
            Authenticated ZaloClient or None if no token
        """
        token = self.get_token(broker_id)
        if not token:
            return None
        
        return ZaloClient(app_id, app_secret, token)


# Convenience function for getting client from environment
def get_zalo_client() -> ZaloClient:
    """
    Get Zalo client using credentials from environment variables
    
    Environment variables:
        ZALO_APP_ID: Zalo App ID
        ZALO_APP_SECRET: Zalo App Secret  
        ZALO_ACCESS_TOKEN: OAuth access token
    
    Returns:
        Configured ZaloClient
    """
    app_id = os.getenv('ZALO_APP_ID')
    app_secret = os.getenv('ZALO_APP_SECRET')
    access_token = os.getenv('ZALO_ACCESS_TOKEN')
    
    if not app_id or not app_secret:
        raise ValueError("ZALO_APP_ID and ZALO_APP_SECRET must be set")
    
    return ZaloClient(app_id, app_secret, access_token)
