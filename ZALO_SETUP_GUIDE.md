## Zalo Integration Setup Guide

Complete guide to connect your AI assistant to Zalo for real-world testing.

---

## Step 1: Create Zalo Official Account

### 1.1 Register Official Account

1. Go to [Zalo Official Account](https://oa.zalo.me/)
2. Click "Đăng ký" (Register)
3. Fill in your business information
4. Choose account type: "Cá nhân" (Personal) for testing
5. Complete verification

### 1.2 Create Developer App

1. Go to [Zalo For Developers](https://developers.zalo.me/)
2. Login with your Zalo account
3. Create new application:
   - App name: "AI Broker Assistant" (or your choice)
   - Category: Business/Real Estate
4. Note down:
   - **App ID** (looks like: `1234567890`)
   - **App Secret** (long string)

---

## Step 2: Configure Webhook

### 2.1 Expose Local Server

For testing locally, use ngrok to expose your FastAPI server:

```bash
# Install ngrok (if not installed)
brew install ngrok

# Start your FastAPI server
uvicorn main:app --reload --port 8000

# In another terminal, expose it
ngrok http 8000
```

Copy the ngrok HTTPS URL (e.g., `https://abc123.ngrok.io`)

### 2.2 Set Webhook in Zalo Dashboard

1. Go to Zalo Developers dashboard
2. Select your app
3. Navigate to "Webhook" settings
4. Enter webhook URL: `https://abc123.ngrok.io/zalo/webhook`
5. Set verify token: `zalo_broker_assistant_2026` (or any secure string)
6. Click "Verify" - Zalo will send a GET request
7. If successful, click "Subscribe" to events:
   - ✅ `user_send_text` - When users send text messages
   - ✅ `user_send_image` - When users send images (optional)

---

## Step 3: Get OAuth Access Token

### Option A: For Your Personal Testing

1. Go to Zalo Developers → Your App → "Access Token"
2. Click "Get Token"
3. Login with Zalo account you want to test with
4. Grant permissions
5. Copy the **Access Token** (long string)
6. Save it - this token works for your account

### Option B: For Your Cousin's Account

Your cousin needs to:
1. Go to your app's OAuth URL (get from Zalo dashboard)
2. Login with their Zalo account
3. Grant permissions
4. App receives their access token
5. You save it using `/zalo/auth/save-token` endpoint

---

## Step 4: Configure Environment Variables

Create `.env` file in project root:

```bash
# Zalo API Credentials
ZALO_APP_ID=your_app_id_here
ZALO_APP_SECRET=your_app_secret_here
ZALO_ACCESS_TOKEN=your_access_token_here
ZALO_VERIFY_TOKEN=zalo_broker_assistant_2026

# Default broker (for single-user testing)
DEFAULT_BROKER_ID=your_name
```

Load environment variables:

```bash
# Install python-dotenv
pip install python-dotenv

# Add to main.py (already included)
from dotenv import load_dotenv
load_dotenv()
```

---

## Step 5: Test the Integration

### 5.1 Start Server

```bash
uvicorn main:app --reload --port 8000
```

### 5.2 Send Test Message

1. Open Zalo app on your phone
2. Search for your Official Account
3. Send a message:
   ```
   Chào em, anh muốn tìm căn hộ 2PN ở Quận 2, tầm 2-3 tỷ
   ```

### 5.3 What Should Happen

1. ✅ Zalo sends message to your webhook
2. ✅ Listener extracts: budget, location, intent
3. ✅ Strategist decides: quick_reply
4. ✅ Closer generates Vietnamese suggestion
5. ✅ AI responds automatically in Zalo chat!

### 5.4 Check Logs

```bash
# In terminal where uvicorn is running, you'll see:
INFO: POST /zalo/webhook - 200
```

---

## Step 6: Multi-User Setup (You + Cousin)

### 6.1 Architecture

```
You (Broker 1) → Zalo Account 1 → Access Token 1
Cousin (Broker 2) → Zalo Account 2 → Access Token 2

Both use the same AI assistant
Separate lead databases per broker
```

### 6.2 Get Cousin's Token

1. **Cousin completes OAuth flow:**
   ```
   https://oauth.zalo.me/v4/oa/permission?
   app_id=YOUR_APP_ID&
   redirect_uri=YOUR_REDIRECT_URI&
   state=cousin_broker_id
   ```

2. **After auth, Zalo redirects with code:**
   ```
   YOUR_REDIRECT_URI?code=ABC123&state=cousin_broker_id
   ```

3. **Exchange code for token:**
   ```bash
   curl -X POST https://oauth.zalo.me/v4/oa/access_token \
     -H "Content-Type: application/json" \
     -d '{
       "app_id": "YOUR_APP_ID",
       "app_secret": "YOUR_APP_SECRET",
       "code": "ABC123"
     }'
   ```

4. **Save cousin's token:**
   ```bash
   curl -X POST http://localhost:8000/zalo/auth/save-token \
     -H "Content-Type: application/json" \
     -d '{
       "broker_id": "cousin_name",
       "access_token": "cousin_access_token",
       "refresh_token": "cousin_refresh_token"
     }'
   ```

### 6.3 Update Webhook Handler

Modify `integrations/zalo_routes.py` to map Zalo user ID to broker:

```python
# Map user to broker (add at top of file)
USER_TO_BROKER_MAP = {
    "your_zalo_user_id": "your_broker_id",
    "cousin_zalo_user_id": "cousin_broker_id"
}

# In webhook handler:
broker_id = USER_TO_BROKER_MAP.get(user_id, "default_broker")
```

---

## Step 7: Production Deployment

### 7.1 Deploy to Cloud

```bash
# Use Railway, Render, or any platform
# They provide permanent HTTPS URLs

# Update webhook URL in Zalo dashboard
# From: https://abc123.ngrok.io/zalo/webhook
# To: https://your-app.railway.app/zalo/webhook
```

### 7.2 Secure Your Tokens

```bash
# Never commit .env to git
echo ".env" >> .gitignore

# Use platform's environment variables
# Railway: Settings → Variables
# Render: Environment → Add Variable
```

---

## Troubleshooting

### Issue: Webhook verification fails

**Fix:**
- Check ZALO_VERIFY_TOKEN matches in:
  - `.env` file
  - Zalo dashboard settings
  - `/zalo/webhook` GET endpoint

### Issue: No response from AI

**Check:**
1. ngrok is running: `curl https://abc123.ngrok.io`
2. FastAPI is running: `curl http://localhost:8000`
3. Logs show webhook received: Check uvicorn terminal
4. Access token is valid: Try sending manually

### Issue: "Broker not authenticated"

**Fix:**
```bash
# Save your token:
curl -X POST http://localhost:8000/zalo/auth/save-token \
  -H "Content-Type: application/json" \
  -d '{
    "broker_id": "your_name",
    "access_token": "YOUR_ACTUAL_TOKEN_HERE",
    "refresh_token": "YOUR_REFRESH_TOKEN_HERE"
  }'
```

---

## Testing Checklist

- [ ] Zalo Official Account created
- [ ] Developer app created (App ID + Secret)
- [ ] Webhook URL set in Zalo dashboard
- [ ] Webhook verified successfully
- [ ] `.env` file configured
- [ ] Server running with ngrok
- [ ] Test message sent from Zalo
- [ ] AI responds automatically
- [ ] Lead data saved in `data/leads/`
- [ ] Conversation logged in `data/conversations/`

---

## Next Steps

1. **Test with real conversations:**
   - Use your own Zalo account
   - Send various property inquiries
   - Review AI suggestions quality

2. **Refine AI responses:**
   - Adjust message templates in `agents/closer.py`
   - Fine-tune Vietnamese language patterns
   - Add more persuasion tactics

3. **Invite your cousin:**
   - Guide them through OAuth flow
   - Save their token
   - Test multi-user support

4. **Production deployment:**
   - Deploy to cloud platform
   - Update webhook URL
   - Monitor performance

---

## Support

If you encounter issues:

1. Check FastAPI logs: `tail -f nohup.out`
2. Test webhook manually:
   ```bash
   curl -X POST http://localhost:8000/zalo/webhook \
     -H "Content-Type: application/json" \
     -d '{
       "event": "user_send_text",
       "sender": {"id": "test_user"},
       "message": {"text": "Chào em"},
       "timestamp": 1234567890
     }'
   ```
3. Verify Zalo API docs: https://developers.zalo.me/docs

---

**Ready to connect to Zalo!** 🚀

Start with Step 1 and work through each section.
