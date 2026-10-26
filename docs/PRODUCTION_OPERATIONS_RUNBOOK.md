# AICTE Sentinel — Production Operations & Deployment Runbook

**Problem Statement ID:** Smart India Hackathon (SIH) 2026 — Problem Statement 26262  
**System Name:** AICTE Sentinel — Statutory Approval Workflow & Compliance Intelligence Platform  
**Target Architecture:** Vercel (React Frontend) + Render / Cloud Engine (FastAPI Backend) + Managed PostgreSQL  
**Repository:** [https://github.com/muditk-dev/aicte-sentinel](https://github.com/muditk-dev/aicte-sentinel)  
**Frontend URL:** [https://aicte-sentinel-theta.vercel.app](https://aicte-sentinel-theta.vercel.app)  

---

## 1. System Topology Overview

```mermaid
flowchart LR
    A["GitHub Repository (muditk-dev/aicte-sentinel)"] -->|Automated Git Hook| B["Vercel Edge (Frontend SPA)"]
    A -->|Render Blueprint (render.yaml)| C["Render Web Service (FastAPI)"]
    C -->|Asyncpg Connection Pool| D["Managed PostgreSQL (aicte-sentinel-postgres)"]
    B -->|REST API Calls (VITE_API_BASE_URL)| C
```

---

## 2. Deploying the Cloud Backend (Render 1-Click Blueprint)

To pair the deployed Vercel frontend with a live cloud backend and persistent PostgreSQL database:

### Step 1: Connect GitHub Repo in Render
1. Navigate to [https://dashboard.render.com](https://dashboard.render.com).
2. Click **New +** in the top navigation bar and select **Blueprint**.
3. Connect your GitHub account (`muditk-dev`) and choose the repository `aicte-sentinel`.
4. Render will parse [`render.yaml`](file:///C:/Users/mudit/Downloads/26262/render.yaml) automatically:
   - **Service 1:** `aicte-sentinel-backend` (FastAPI Python Web Service, Free Tier).
   - **Database 1:** `aicte-sentinel-postgres` (Managed PostgreSQL 16, Free Tier).
5. Click **Apply**. Render will provision the PostgreSQL instance and deploy the backend.

### Step 2: Run Alembic Database Migrations on Cloud PostgreSQL
Once the Render database is provisioned:
```bash
# In the Render Web Service shell or from your local machine with DATABASE_URL set:
alembic upgrade head
```
*This executes all 6 migrations up to `006_postgresql_rls` on the physical PostgreSQL database, enabling Row-Level Security policies.*

### Step 3: Seed Synthetic Demonstration Data on Cloud PostgreSQL
```bash
python scripts/seed_data.py
```
*Seeds the 3 sample technical colleges, 5 statutory personas, sample dockets, APH 2026-27 clauses, and verifies the SHA-256 audit ledger.*

### Step 4: Link Vercel Frontend to Render Backend
1. Open the [Vercel Dashboard](https://vercel.com/dashboard).
2. Select the `aicte-sentinel` project -> **Settings** -> **Environment Variables**.
3. Add a new variable:
   - **Key:** `VITE_API_BASE_URL`
   - **Value:** `https://aicte-sentinel-backend.onrender.com` (use your actual Render backend URL).
   - **Target:** Production.
4. Go to **Deployments**, click the three dots on the latest deployment, and select **Redeploy** to bake the new API base into the bundle.

---

## 3. Routine Operations & Maintenance Procedures

### 3.1 Redeploying Frontend Updates
To push an update to Vercel:
```powershell
# From local workspace (C:\Users\mudit\Downloads\26262):
npm --prefix frontend run build
npx vercel build --prod --cwd frontend
npx vercel deploy --prebuilt --prod --cwd frontend
```
*(Or commit and push to branch `master`; if GitHub connection is linked in Vercel project settings, automatic CI/CD deployment will trigger on push).*

### 3.2 Updating the GitHub Remote
```powershell
git add .
git commit -m "feat: your update message"
git push origin master
```

### 3.3 Verifying Audit Ledger Health
To audit the cryptographic chain integrity against live tampering:
```powershell
# Local / Remote API check:
curl -s -H "Authorization: Bearer <TOKEN>" https://<BACKEND_URL>/api/v1/audit/verify
```
*Expected response: `{"is_valid": true, "verification_message": "Cryptographic chain verified...", "broken_sequence_id": null}`.*

### 3.4 Managing Vercel Project Protection
If Vercel enables deployment protection on new preview links, disable it via CLI:
```powershell
npx vercel project protection disable aicte-sentinel --sso --cwd frontend
```

---

## 4. Emergency Rollback Procedures

### Frontend Rollback (Vercel)
1. Go to `https://vercel.com/raya25/aicte-sentinel/deployments`.
2. Locate the previous healthy deployment (e.g. `dpl_6YVCqdg1XhzivHCcgeMFJrVwUgg7`).
3. Click the three dots -> **Promote to Production**. Instant rollback takes under 5 seconds.

### Local Demo Fallback
If cloud internet connectivity fails during the live hackathon presentation:
- The local demonstration environment remains **100% operational** on your Windows laptop:
  - Backend: `http://127.0.0.1:8000` (PID 21008)
  - Frontend: `http://127.0.0.1:5173` (PID 14236)
  - Database: `sentinel_dev.db` (local SQLite fallback)
