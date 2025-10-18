# 🚀 Quick Start: Fly.io CI/CD

**Goal:** Auto-deploy to Fly.io on every push to `main`

## ⚡ 5-Minute Setup

### 1️⃣ Create Deploy Token
```bash
flyctl tokens create deploy -x 999999h
```
Copy the FULL output (including "FlyV1 ")

### 2️⃣ Add to GitHub
1. Go to: https://github.com/Adriaan11/tailorblend-backend-api/settings/secrets/actions
2. New secret: `FLY_API_TOKEN`
3. Paste token → Save

### 3️⃣ Set Fly Secrets (if not done already)
```bash
flyctl secrets set OPENAI_API_KEY=sk-proj-your-key-here
```

### 4️⃣ Push to GitHub
```bash
git add .
git commit -m "Setup Fly.io CI/CD with optimized config"
git push origin main
```

### 5️⃣ Watch Deployment
https://github.com/Adriaan11/tailorblend-backend-api/actions

---

## ✅ What Was Configured

**Files Created:**
- `.github/workflows/fly.yml` - GitHub Actions workflow
- `.github/DEPLOY_SETUP.md` - Full setup guide
- `.github/QUICK_START.md` - This file

**fly.toml Changes:**
- Memory: 512MB → **256MB** (47% cost savings)
- Swap: Added **512MB** safety buffer
- Cost: **$2.02/month** (~R37 ZAR)
- Always-on: ✅ Configured

**What Happens Now:**
Every push to `main` → Auto-deploy to Fly.io (Johannesburg)

---

## 📋 Checklist

- [ ] Run: `flyctl tokens create deploy -x 999999h`
- [ ] Add `FLY_API_TOKEN` to GitHub secrets
- [ ] Set `OPENAI_API_KEY` in Fly: `flyctl secrets set OPENAI_API_KEY=...`
- [ ] Commit and push changes
- [ ] Verify deployment at https://github.com/Adriaan11/tailorblend-backend-api/actions
- [ ] Test API: `curl https://tailorblend-api.fly.dev/api/health`

---

**Need help?** See `.github/DEPLOY_SETUP.md` for detailed instructions.
