# Fly.io GitHub Actions CI/CD Setup Guide

This guide walks you through setting up automatic deployment to Fly.io whenever you push to the `main` branch.

## ✅ What's Already Done

1. ✅ GitHub Actions workflow created (`.github/workflows/fly.yml`)
2. ✅ fly.toml configured for cheapest always-on setup (256MB @ $2.02/month)
3. ✅ Repository connected to GitHub: https://github.com/Adriaan11/tailorblend-backend-api

## 🚀 Remaining Setup Steps

### Step 1: Install Fly CLI (if not already installed)

**macOS:**
```bash
brew install flyctl
```

**Linux/WSL:**
```bash
curl -L https://fly.io/install.sh | sh
```

**Verify installation:**
```bash
flyctl version
```

### Step 2: Authenticate with Fly.io

```bash
flyctl auth login
```

This will open your browser for authentication.

### Step 3: Create Fly App (First-Time Only)

**If app doesn't exist yet:**
```bash
cd /Users/adriaancroucamp/Developer/TailorBlend/tailorblend-backend-api
flyctl launch --no-deploy
```

Follow prompts:
- App name: `tailorblend-api` (or choose your own)
- Region: `jnb` (Johannesburg) - already configured in fly.toml
- Confirm settings

**If app already exists:**
Skip to Step 4.

### Step 4: Set Fly.io Secrets

Your API needs the OpenAI API key in production:

```bash
# Set OpenAI API key (REQUIRED)
flyctl secrets set OPENAI_API_KEY=sk-proj-your-key-here

# Set CORS origins for production frontend (OPTIONAL)
flyctl secrets set CORS_ALLOWED_ORIGINS="https://yourdomain.com"
```

**Check secrets:**
```bash
flyctl secrets list
```

### Step 5: Generate Deploy Token

Create a long-lived token for GitHub Actions:

```bash
flyctl tokens create deploy -x 999999h
```

**IMPORTANT:** Copy the ENTIRE output, including "FlyV1" prefix and the space after it.

Example output:
```
FlyV1 fm2_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Step 6: Add Secret to GitHub

1. Go to: https://github.com/Adriaan11/tailorblend-backend-api/settings/secrets/actions
2. Click **"New repository secret"**
3. Name: `FLY_API_TOKEN`
4. Value: Paste the FULL token from Step 5 (including "FlyV1 ")
5. Click **"Add secret"**

### Step 7: Test Deployment

**Option A: Manual deploy to verify everything works**
```bash
flyctl deploy
```

**Option B: Trigger GitHub Action**
```bash
git add .
git commit -m "Setup Fly.io CI/CD"
git push origin main
```

Then check: https://github.com/Adriaan11/tailorblend-backend-api/actions

## 📊 How It Works

1. **Push to main** → GitHub Actions triggered
2. **GitHub Action** → Checks out code, sets up flyctl
3. **Deploy** → Runs `flyctl deploy --remote-only` using `FLY_API_TOKEN`
4. **Fly.io** → Builds Docker image, deploys to 256MB VM in Johannesburg
5. **Health check** → Verifies `/api/health` endpoint responds
6. **Live** → Your API is accessible at `https://tailorblend-api.fly.dev`

## 🔍 Monitoring & Debugging

**View logs:**
```bash
flyctl logs
```

**Check app status:**
```bash
flyctl status
```

**Check resource usage:**
```bash
flyctl vm status
```

**SSH into machine:**
```bash
flyctl ssh console
```

**View GitHub Action runs:**
https://github.com/Adriaan11/tailorblend-backend-api/actions

## 💰 Cost Optimization

Current configuration:
- **VM**: 256MB shared CPU = $2.02/month
- **Swap**: 512MB (free, just uses disk)
- **Always-on**: `auto_stop_machines = off`, `min_machines_running = 1`
- **No scale**: Single machine (no redundancy)

**Total: ~$2.02/month (~R37 ZAR)**

If you experience OOM errors:
1. Edit `fly.toml` line 40: change to `memory = "512mb"`
2. Push to GitHub (auto-deploys)
3. New cost: $3.32/month

## 🔒 Security Notes

- ✅ API key stored in Fly secrets (not in code)
- ✅ Deploy token stored in GitHub secrets (not exposed)
- ✅ HTTPS enforced via `force_https = true`
- ✅ Docker runs as non-root user (security best practice)
- ✅ GitHub Actions workflow has no command injection risks

## 🛠️ Troubleshooting

### "App not found"
Run `flyctl launch --no-deploy` first to create the app.

### "Unauthorized"
- Verify `FLY_API_TOKEN` is set correctly in GitHub secrets
- Token must include "FlyV1 " prefix
- Try regenerating token: `flyctl tokens create deploy -x 999999h`

### "Health check failed"
- Check logs: `flyctl logs`
- Verify `/api/health` endpoint works locally
- Increase grace period in fly.toml if startup is slow

### "Out of memory"
- Upgrade to 512MB: edit fly.toml line 40
- Monitor with: `flyctl vm status`

### GitHub Action fails
- Check action logs: https://github.com/Adriaan11/tailorblend-backend-api/actions
- Verify `FLY_API_TOKEN` secret exists in repo settings
- Ensure fly.toml is committed to repo

## 📚 Resources

- Fly.io Docs: https://fly.io/docs
- GitHub Actions: https://docs.github.com/en/actions
- Pricing Calculator: https://fly.io/calculator
- Community Forum: https://community.fly.io

---

**Ready to deploy?** Follow Steps 1-7 above, then push to main! 🚀
