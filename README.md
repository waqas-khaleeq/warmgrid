# ⚡ WarmGrid

**Self-hosted email warmup engine.** Automates the full warmup process for sender mailboxes using a pool of seed accounts — sending realistic emails, auto-replying, rescuing spam, tracking health scores, and monitoring blacklists.

![WarmGrid Dashboard](https://placehold.co/1200x600/0a0a0f/6366f1?text=WarmGrid+Dashboard&font=montserrat)

---

## Features

- **Automated warmup sends** — daily emails sent within a configurable time window with human-like random delays
- **Seed pool management** — import 30+ Gmail/Outlook seed accounts via CSV
- **Auto-reply engine** — seeds automatically reply to warmup emails
- **Spam rescue** — detects and moves emails from spam/junk back to inbox
- **Volume ramping** — automatically increases daily send volume each week
- **Health scoring** — 0–100 score per mailbox based on spam rate, reply rate, bounce rate, and blacklist status
- **DNS blacklist checks** — checks 6 major blacklists (Spamhaus, Barracuda, SpamCop, SORBS, etc.)
- **Content deduplication** — SHA-256 tracking ensures no seed ever receives the same content twice
- **DeepSeek AI mode** — optionally generate unique email content via DeepSeek API
- **Real-time CSV import** — SSE-powered live progress when bulk importing seeds
- **Dark dashboard** — clean data-first UI with charts, activity feed, and health badges

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11 + FastAPI |
| Database | PostgreSQL (production) / SQLite (local) via SQLAlchemy async |
| Scheduler | APScheduler 3.x (5 background jobs) |
| Email Sending | aiosmtplib (async SMTP) |
| Email Receiving | aioimaplib (async IMAP) |
| Auth | JWT + bcrypt |
| Frontend | React 18 + Vite + TailwindCSS |
| Charts | Recharts |
| AI Content | DeepSeek API (optional) |

---

## Quick Start (Local)

### Prerequisites
- Python 3.11+
- Node.js 18+ with npm or pnpm

### 1. Clone and set up

```bash
git clone https://github.com/YOUR_USERNAME/warmgrid.git
cd warmgrid
```

### 2. Backend setup

```bash
cd backend
python -m venv venv

# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Create environment file

```bash
cp .env.example .env
```

Generate your keys (run once):

```python
python -c "from cryptography.fernet import Fernet; print('ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
python -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"
```

Paste those values into `backend/.env`.

### 4. Start the backend

```bash
uvicorn main:app --reload
# Running at http://localhost:8000
```

### 5. Frontend setup

```bash
cd ../frontend
npm install        # or: pnpm install
npm run dev        # or: pnpm run dev
# Running at http://localhost:5173
```

### 6. Open the app

Visit **http://localhost:5173** → Create your admin account → start adding mailboxes.

---

## Deployment (Free — No Credit Card)

| Service | Platform | Cost |
|---|---|---|
| Backend | Render.com (free web service) | $0 |
| Database | Neon.tech (free PostgreSQL) | $0 |
| Frontend | Vercel (free) | $0 |
| Keep-alive | UptimeRobot (free monitor) | $0 |

### Step 1 — Get free PostgreSQL from Neon

1. Sign up at **https://neon.tech** (GitHub login, no card)
2. Create a new project → copy the **Connection String**

### Step 2 — Deploy backend to Render

1. Sign up at **https://render.com** (GitHub login, no card)
2. New → Web Service → connect this repo
3. Settings:
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Free
4. Add environment variables:

| Key | Value |
|---|---|
| `DATABASE_URL` | Your Neon connection string |
| `ENCRYPTION_KEY` | Generated Fernet key |
| `SECRET_KEY` | Generated random hex |
| `FRONTEND_URL` | Your Vercel URL (add after step 3) |

### Step 3 — Deploy frontend to Vercel

1. Sign up at **https://vercel.com** (GitHub login, no card)
2. New Project → import this repo
3. **Root Directory:** `frontend`
4. Environment variable: `VITE_API_URL` = `https://your-render-app.onrender.com`
5. Deploy

### Step 4 — Keep Render awake (important)

Render free tier sleeps after 15 min. This stops the scheduler.

1. Sign up at **https://uptimerobot.com** (free)
2. Add HTTP monitor → URL: `https://your-render-app.onrender.com/health`
3. Interval: **5 minutes**

Your scheduler now runs 24/7.

---

## Adding Your First Sender Mailbox

1. Go to **Mailboxes** → **Add Mailbox**
2. Select provider — Microsoft 365 or Gmail auto-fills SMTP/IMAP settings
3. Enter credentials and click **Test SMTP** / **Test IMAP**
4. Both must pass before saving
5. Set target daily volume (recommended: start at 20–30)

### Microsoft 365 SMTP Auth

M365 blocks SMTP auth by default. Enable it:

```
M365 Admin Center → Exchange → Recipients → Mailboxes
→ select mailbox → Mail flow settings
→ Enable: Authenticated SMTP
```

Or via PowerShell:
```powershell
Set-CASMailbox user@domain.com -SmtpClientAuthenticationDisabled $false
```

---

## Importing Seed Accounts via CSV

1. Go to **Seed Pool** → **Import CSV**
2. Download the template
3. Fill in your seed Gmail/Outlook accounts:

```csv
email,app_password
seed1@gmail.com,xxxx-xxxx-xxxx-xxxx
seed2@gmail.com,yyyy-yyyy-yyyy-yyyy
```

4. Upload → watch real-time progress per account

### Gmail App Passwords

Gmail requires App Passwords (not your regular password):

1. Google Account → **Security** → enable **2-Step Verification**
2. Search **App Passwords** → create one for "Mail"
3. Copy the 16-character code (remove spaces)

---

## Warmup Schedule

WarmGrid automatically ramps volume every Monday:

| Week | Daily Sends | Notes |
|---|---|---|
| 1 | 5 | Establish sender reputation |
| 2 | 10 | Seeds start replying |
| 3 | 15 | Spam rescue active |
| 4 | 20 | Ramp continues |
| 5–8 | +5/week | Approaching target |
| 9+ | Target | Full volume |

---

## Health Score

Calculated daily per mailbox (0–100):

| Factor | Deduction |
|---|---|
| Spam rate > 10% | −35 pts |
| Reply rate < 20% | −25 pts |
| Bounce rate > 5% | −20 pts |
| Volume ramp off-track | −10 pts |
| On DNS blacklist | −10 pts |

- **80–100** 🟢 Excellent
- **50–79** 🟡 Monitor closely
- **0–49** 🔴 Auto-paused — investigate

---

## Content Engine

### Static Templates (default)
60 subject lines × 100 body templates = 6,000 unique combinations per sender/seed pair. Auto-resets when 80% exhausted.

### DeepSeek AI Mode
Every email uniquely generated by AI. Falls back to templates if API is unavailable.

**Enable:**
1. Settings → Content Engine → toggle **DeepSeek AI**
2. Enter API key from **https://platform.deepseek.com**
3. Click **Test API Key** → Save

**Cost estimate:** ~$0.004/day at 250 emails/day. Essentially free.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | ✅ | JWT signing key (random 32-byte hex) |
| `ENCRYPTION_KEY` | ✅ | Fernet key for encrypting stored passwords |
| `DATABASE_URL` | ✅ | SQLite (local) or PostgreSQL (production) |
| `FRONTEND_URL` | Production | Your Vercel frontend URL (for CORS) |

---

## Project Structure

```
warmgrid/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Environment settings
│   ├── database.py          # SQLAlchemy async engine (SQLite + PostgreSQL)
│   ├── models.py            # All database models
│   ├── schemas.py           # Pydantic request/response schemas
│   ├── auth.py              # JWT + bcrypt authentication
│   ├── scheduler.py         # 5 APScheduler background jobs
│   ├── smtp_sender.py       # Async SMTP engine
│   ├── imap_listener.py     # Async IMAP engine
│   ├── content_engine.py    # Templates + DeepSeek + deduplication
│   ├── health_monitor.py    # Health score calculation
│   ├── blacklist_checker.py # DNS blacklist checks
│   ├── seed_importer.py     # CSV parser + provider detection
│   ├── routers/
│   │   ├── auth.py          # Login, setup, JWT
│   │   ├── mailboxes.py     # Sender mailbox CRUD
│   │   ├── seeds.py         # Seed pool + CSV import SSE
│   │   ├── logs.py          # Activity logs + CSV export
│   │   ├── analytics.py     # Dashboard stats
│   │   └── settings.py      # App settings + DeepSeek test
│   ├── requirements.txt
│   ├── .env.example
│   └── render.yaml          # Render.com deployment config
├── frontend/
│   ├── src/
│   │   ├── pages/           # Dashboard, Mailboxes, Seeds, Logs, Settings
│   │   ├── components/      # Reusable UI components
│   │   ├── api/client.js    # Axios instance
│   │   └── context/         # Auth context
│   ├── vercel.json          # Vercel SPA routing
│   └── package.json
├── .gitignore
└── README.md
```

---

## Troubleshooting

**Authentication failed (Gmail)**
→ Use an App Password, not your regular password. 2FA must be on.

**535 error (Microsoft 365)**
→ SMTP Auth is disabled. Enable it in M365 Admin Center (see above).

**Connection refused**
→ Wrong host or port. Gmail: `smtp.gmail.com:587`, M365: `smtp.office365.com:587`

**IMAP disabled (Gmail)**
→ Gmail Settings → See all settings → Forwarding and POP/IMAP → Enable IMAP

**DeepSeek API invalid key**
→ Check at https://platform.deepseek.com — key must start with `sk-`

**Render service sleeping (scheduler stops)**
→ Set up UptimeRobot monitor pinging `/health` every 5 minutes

**Database connection error (Neon)**
→ Make sure `DATABASE_URL` includes `?sslmode=require` at the end

---

## License

MIT License — free to use, modify, and self-host.
