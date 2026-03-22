# Setup api.thucldnguyen.com → Railway

## Step 1: Get Railway URL

From Railway dashboard → Settings → Networking → Generate Domain

Example: `zalo-ai-broker-production-abc123.up.railway.app`

## Step 2: Add CNAME in Netlify

1. Go to https://app.netlify.com/sites/thucldnguyen/dns
2. Click **"Add new record"**
3. Fill in:
   - **Record type:** CNAME
   - **Name:** api
   - **Value:** YOUR-RAILWAY-URL.up.railway.app (paste from Railway)
   - **TTL:** 3600
4. Click **"Save"**

## Step 3: Wait for DNS Propagation (2-5 min)

Test with:
```bash
# Check if DNS is ready
dig api.thucldnguyen.com

# Test API endpoint
curl https://api.thucldnguyen.com
```

You should see: `{"status":"running","app":"Zalo AI Broker Assistant"...}`

## Step 4: Setup Zalo Webhook

### 4A: Add Domain Verification (if Zalo requires)

Zalo may ask you to verify ownership by adding a TXT record.

They'll show you something like:
- **Record type:** TXT
- **Name:** `_zalo-verify` or `@`
- **Value:** `zalo-site-verification=ABC123XYZ...`

Add this in Netlify DNS the same way (choose TXT instead of CNAME).

### 4B: Configure Webhook

In Zalo Developer Dashboard:
1. Go to Webhook settings
2. **Webhook URL:** `https://api.thucldnguyen.com/zalo/webhook`
3. **Verify Token:** `zalo_broker_assistant_2026`
4. Click **"Verify"** - Should succeed! ✅
5. **Subscribe to events:** Check `user_send_text`

## Step 5: Get OAuth Access Token

In Zalo Developer Dashboard:
1. Look for **"Access Token"** or **"Get Token"** section
2. Click to generate token for your Official Account
3. Login with your Zalo account
4. Copy the access token

## Step 6: Update Railway Environment Variable

Back in Railway:
1. Go to Variables tab
2. Find `ZALO_ACCESS_TOKEN`
3. Update with the real token (replace `your_token_here`)
4. Railway will auto-redeploy

## Step 7: Test It!

Open Zalo app → Message your Official Account:
```
Chào em, anh muốn tìm căn hộ 2PN ở Quận 2, tầm 3 tỷ
```

AI should respond automatically! 🎉

---

## Troubleshooting

### DNS not resolving
```bash
# Wait a few more minutes, then:
dig api.thucldnguyen.com +short
# Should show Railway IP
```

### Webhook verification fails
- Check verify token matches: `zalo_broker_assistant_2026`
- Check URL is exactly: `https://api.thucldnguyen.com/zalo/webhook`
- Check Railway deployment is running: Visit `https://YOUR-RAILWAY-URL.up.railway.app/`

### No AI response
- Check Railway logs for errors
- Verify `ZALO_ACCESS_TOKEN` is set correctly
- Test locally: `curl https://api.thucldnguyen.com/process -X POST -H "Content-Type: application/json" -d '{"lead_id":"test","message":"test"}'`
