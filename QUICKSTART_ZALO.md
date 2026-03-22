# Quick Start: Connect to Zalo (5 minutes)

Fastest way to test the AI assistant with your Zalo account.

---

## Prerequisites

- ✅ MVP code already running (`uvicorn main:app --reload`)
- 📱 Zalo app on your phone
- 💻 Terminal access

---

## Step 1: Get Zalo Credentials (2 min)

### Option A: Use Existing Zalo OA (if you have one)

1. Login to [Zalo Developers](https://developers.zalo.me/)
2. Find your app
3. Copy **App ID** and **App Secret**
4. Go to "Access Token" → Get Token
5. Copy **Access Token**

### Option B: Quick Test Mode (recommended for first try)

I'll help you get test credentials - message me your Zalo phone number and I'll set up a test app for you.

---

## Step 2: Configure Environment (1 min)

```bash
cd ~/Documents/GitHub/zalo-ai-broker

# Copy example env file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

Paste your credentials:
```bash
ZALO_APP_ID=1234567890
ZALO_APP_SECRET=abc123def456...
ZALO_ACCESS_TOKEN=xyz789...
ZALO_VERIFY_TOKEN=zalo_broker_assistant_2026
DEFAULT_BROKER_ID=thuc
```

Save (Ctrl+O, Enter, Ctrl+X)

---

## Step 3: Expose Server to Internet (1 min)

```bash
# Install ngrok (if not installed)
brew install ngrok

# Start ngrok (in a new terminal)
ngrok http 8000
```

Copy the HTTPS URL shown (e.g., `https://abc123.ngrok.io`)

---

## Step 4: Set Webhook in Zalo (1 min)

1. Go to [Zalo Developers](https://developers.zalo.me/) → Your App
2. Click "Webhook" in sidebar
3. Enter webhook URL: `https://abc123.ngrok.io/zalo/webhook`
4. Enter verify token: `zalo_broker_assistant_2026`
5. Click "Verify" ✅
6. Click "Subscribe to events":
   - ✅ user_send_text

---

## Step 5: Test It! (30 seconds)

### 5.1 Restart Server

```bash
# Stop server (Ctrl+C) and restart to load .env
uvicorn main:app --reload
```

### 5.2 Send Test Message

📱 Open Zalo → Search for your Official Account → Send:

```
Chào em, anh muốn tìm căn hộ 2PN ở Quận 2, tầm 2-3 tỷ
```

### 5.3 AI Should Respond!

You'll get a Vietnamese reply like:

> Dạ anh, em đang có 2 căn 2PN view sông tuyệt đẹp ở Q2. Một căn tầng 15 giá 2.8 tỷ, một căn tầng 20 giá 3.2 tỷ. Anh muốn em gửi hình không ạ? 📸

---

## ✅ Success Checklist

- [ ] ngrok running and showing HTTPS URL
- [ ] `.env` file has real credentials
- [ ] Webhook verified in Zalo dashboard
- [ ] Server restarted with `load_dotenv()`
- [ ] Test message sent from Zalo app
- [ ] AI responded automatically

---

## Troubleshooting

### "Webhook verification failed"

❌ Check: `ZALO_VERIFY_TOKEN` in `.env` matches what you entered in Zalo dashboard

### "No response from AI"

❌ Check server logs:
```bash
# You should see:
INFO: POST /zalo/webhook - 200
```

If not, your ngrok URL might be wrong or server crashed.

### "Broker not authenticated"

❌ Your access token might be expired or wrong. Get a fresh one from Zalo dashboard.

---

## What's Next?

### Test More Scenarios

Try these messages:
```
Anh đang tìm hiểu thôi, có căn nào view sông không em?
```
```
Budget khoảng 5 tỷ, muốn biệt thự ở Thảo Điền
```
```
Cho anh xem căn đầu tư cho thuê ở Vinhomes
```

### Review AI Suggestions

Check `data/leads/` to see extracted lead profiles:
```bash
cat data/leads/zalo_*.json | jq .
```

### Invite Your Cousin

See [ZALO_SETUP_GUIDE.md](ZALO_SETUP_GUIDE.md) Section 6 for multi-user setup.

---

## Support

Stuck? Check:
1. Server logs: Look at terminal where `uvicorn` is running
2. ngrok dashboard: http://localhost:4040 shows requests
3. Zalo docs: https://developers.zalo.me/docs

---

**You're live!** 🎉

The AI is now responding to real Zalo messages in Vietnamese.
