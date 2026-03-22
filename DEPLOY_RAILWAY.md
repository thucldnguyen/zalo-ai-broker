# Deploy to Railway (Free - 10 minutes)

Railway gives you a free HTTPS domain that Zalo will accept.

## Step 1: Sign up for Railway

1. Go to https://railway.app/
2. Click "Start a New Project"
3. Login with GitHub

## Step 2: Deploy from GitHub

1. Click "Deploy from GitHub repo"
2. Select: `thucldnguyen/zalo-ai-broker`
3. Click "Deploy Now"

## Step 3: Add Environment Variables

In Railway dashboard → Variables → Add:

```
ZALO_APP_ID=2863684291160492589
ZALO_APP_SECRET=LbFu2W6W5967ldeUpPBD
ZALO_ACCESS_TOKEN=your_token_here
ZALO_VERIFY_TOKEN=zalo_broker_assistant_2026
DEFAULT_BROKER_ID=thuc
PORT=8000
```

## Step 4: Get Your Railway URL

1. Railway will deploy automatically
2. Go to Settings → Networking → Generate Domain
3. You'll get something like: `zalo-ai-broker-production.up.railway.app`

## Step 5: Set Zalo Webhook

1. Go back to Zalo Developer dashboard
2. Webhook URL: `https://YOUR-RAILWAY-URL.railway.app/zalo/webhook`
3. Verify token: `zalo_broker_assistant_2026`
4. ✅ Zalo will accept this domain!

---

**After deployment, your AI will be live 24/7!**

No need for ngrok or keeping your laptop running.
