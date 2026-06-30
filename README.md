<div align="center">

# 🧠📬 CortexMail

### *Your inbox, triaged by AI, delivered to your pocket.*

**A multi-account Gmail intelligence agent that watches your inboxes in real time, decides what actually matters, summarizes it, and pings you on Telegram — so you never drown in email again.**

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Agentic_Workflow-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)](https://www.langchain.com/langgraph)
[![OpenAI](https://img.shields.io/badge/GPT--4.1_mini-412991?style=for-the-badge&logo=openai&logoColor=white)](https://platform.openai.com/)
[![Gmail API](https://img.shields.io/badge/Gmail_API-EA4335?style=for-the-badge&logo=gmail&logoColor=white)](https://developers.google.com/gmail/api)
[![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![Telegram](https://img.shields.io/badge/Telegram_Bot-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://core.telegram.org/bots)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)

</div>

---

## ✨ Why CortexMail Exists

Three inboxes. One brain. Zero patience for newsletters.

CortexMail watches **personal, college, and work Gmail accounts simultaneously** via Google Pub/Sub push notifications, runs every new email through an **agentic LangGraph pipeline**, and decides in milliseconds whether it's:

- 🔴 **HIGH PRIORITY** — internships, deadlines, IITM BS coursework, investment actions
- 🟡 **IMPORTANT** — academic notices, club events, people who need a reply
- ⚪ **NOT IMPORTANT** — silently filed away, never bothers you

Only the emails worth your attention get summarized and pushed straight to Telegram. Everything else is labeled and ignored.

---

## 🏗️ System Architecture

```
                              ┌──────────────────────────────────────────┐
                              │              GOOGLE CLOUD                 │
                              │                                            │
   ┌──────────┐   new mail    │   ┌──────────────┐      ┌──────────────┐  │
   │ Personal │──────────────▶│   │  Gmail API   │─────▶│  Pub/Sub     │  │
   │  Gmail   │               │   │   Watch()    │      │   Topic      │  │
   └──────────┘               │   └──────────────┘      └──────┬───────┘  │
   ┌──────────┐               │                                 │          │
   │ College  │──────────────▶│         (3 watch channels,      │          │
   │  Gmail   │               │          auto-renewed every     │          │
   └──────────┘               │          6 days)                │          │
   ┌──────────┐               │                                 │          │
   │   Work   │──────────────▶│                                 │          │
   │  (IITM)  │               │                                 │          │
   └──────────┘               └─────────────────────────────────┼──────────┘
                                                                  │  HTTPS POST
                                                                  ▼
                              ┌───────────────────────────────────────────────┐
                              │            🚀 CORTEXMAIL  (FastAPI)            │
                              │                                                 │
                              │   POST /gmail  ──▶  decode Pub/Sub payload      │
                              │        │                                        │
                              │        ▼                                        │
                              │   BackgroundTasks.add_task(process_email)       │
                              │        │            (instant 200 OK to Google)  │
                              │        ▼                                        │
                              │   ┌─────────────────────────────────────────┐  │
                              │   │   gmail.py :: retrieve_new_emails()      │  │
                              │   │   • Gmail history.list() since last ID   │  │
                              │   │   • Redis dedup  (SET NX, 7-day TTL)     │  │
                              │   │   • fetch + label + extract body         │  │
                              │   └────────────────┬────────────────────────┘  │
                              │                     │  per new email            │
                              │                     ▼                            │
                              │   ┌─────────────────────────────────────────┐  │
                              │   │       🧩 LangGraph Agent Workflow        │  │
                              │   │            (see diagram below)           │  │
                              │   └────────────────┬────────────────────────┘  │
                              └────────────────────┼───────────────────────────┘
                                                    │
                                                    ▼
                                          ┌──────────────────┐
                                          │   📱 Telegram     │
                                          │   Bot Message     │
                                          └──────────────────┘
```

---

## 🧩 The Agent Workflow (LangGraph)

CortexMail's brain is a small but sharp **state graph**: every email flows through specialized agents, with a conditional branch that kills the chain early for anything not worth your time.

```
                         ┌───────────┐
                         │   START   │
                         └─────┬─────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   🧭 decision_node    │
                    │  (decision_agent)    │
                    │                       │
                    │  GPT-4.1-mini reads   │
                    │  sender + subject +   │
                    │  body + receiver ctx  │
                    │                       │
                    │  → HIGH PRIORITY      │
                    │  → IMPORTANT          │
                    │  → NOT IMPORTANT      │
                    └──────────┬────────────┘
                               │
                  ┌────────────┴─────────────┐
                  │      route_decision_node   │
                  └────────────┬─────────────┘
                 NOT IMPORTANT │             │ HIGH PRIORITY / IMPORTANT
                               ▼             ▼
                          ┌────────┐   ┌──────────────────────┐
                          │  END   │   │  📝 summariser_node    │
                          │ (drop) │   │  (summariser_agent)   │
                          └────────┘   │                       │
                                       │  Extracts:             │
                                       │   • headline            │
                                       │   • key_points (≤3)     │
                                       │   • action_required     │
                                       │   • deadline             │
                                       │   • links                │
                                       └───────────┬───────────┘
                                                   ▼
                                       ┌──────────────────────┐
                                       │  🎨 formatter_node     │
                                       │  (generator_agent)    │
                                       │                       │
                                       │  Builds Telegram-     │
                                       │  ready Markdown msg   │
                                       │  with 🔴/🟡 emoji      │
                                       └───────────┬───────────┘
                                                   ▼
                                       ┌──────────────────────┐
                                       │  📨 telegram_node      │
                                       │  (send_message)       │
                                       │                       │
                                       │  Pushes to your        │
                                       │  Telegram chat         │
                                       └───────────┬───────────┘
                                                   ▼
                                              ┌─────────┐
                                              │   END   │
                                              └─────────┘
```

> 💡 **Why a graph and not a script?** Each node is a single-responsibility agent with its own prompt and output schema. Adding a new step (translation, auto-reply drafts, calendar sync) means dropping in one more node — no rewiring the whole pipeline.

---

## 🗂️ Repository Structure

```
CortexMail/
├── 🚪 main.py              FastAPI app · Pub/Sub webhook · watch-renewal scheduler
├── 🧠 agent_workflow.py    LangGraph StateGraph definition (the agent pipeline)
├── 🤖 agents.py            The three LLM agents: decision · summariser · generator
├── ✉️  gmail.py             Gmail OAuth · history sync · Redis dedup · label management
├── 📲 telegram_bot.py      Minimal Telegram Bot API client
├── 🐳 Dockerfile           python:3.13 slim runtime, uvicorn entrypoint
├── 📦 requirements.txt     fastapi · langchain-openai · langgraph · google-api · redis · apscheduler
└── 🔐 accounts/            Per-account OAuth tokens (personal / college / IITM)
```

---

## ⚙️ How a Single Email Travels Through the System

| Step | Component | What Happens |
|------|-----------|---------------|
| **1** | **Gmail Watch** | Each of the 3 mailboxes has an active `users.watch()` subscription pushing to a shared Pub/Sub topic |
| **2** | **`/gmail` webhook** | FastAPI decodes the base64 Pub/Sub payload to find *which* account got new mail |
| **3** | **Instant ACK** | The request is handed to `BackgroundTasks` so Google gets a `200 OK` immediately — no webhook timeouts |
| **4** | **History diff** | `retrieve_new_emails()` compares Gmail's `historyId` against the last seen value (stored in **Redis**) to fetch only *new* messages |
| **5** | **Dedup lock** | A Redis `SET NX` claims each `msg_id` atomically — safe even with multiple workers or replayed Pub/Sub events |
| **6** | **Label + extract** | The email gets Gmail-labeled per account, and plain-text body is recursively extracted from MIME parts |
| **7** | **Decision agent** | GPT-4.1-mini classifies priority using rich personal context (SSN College, IITM BS program, INDmoney investments) |
| **8** | **Conditional routing** | `NOT IMPORTANT` → graph ends silently. Anything else → continues to summarization |
| **9** | **Summary agent** | Extracts headline, key points, action items, deadlines, and links as structured JSON |
| **10** | **Formatter agent** | Renders a clean, emoji-coded Markdown message |
| **11** | **Telegram push** | Message lands in your chat — usually within a couple seconds of the email arriving |

---

## 🔑 Core Capabilities

<table>
<tr>
<td width="50%" valign="top">

### 🔄 Real-Time, Not Polling
Built on Gmail's native **push notifications** via Pub/Sub — emails are processed the moment they arrive, not on a cron schedule.

### 🧠 Context-Aware Classification
The decision agent isn't a generic spam filter — it's been prompt-engineered with deep personal context: college domain rules, IITM BS academic calendar, and personal finance/investment triggers.

### 🪪 Multi-Account, One Brain
Three completely separate Gmail accounts (personal, college, work) are watched concurrently, each authenticated with its own OAuth token, all funneled through one shared agent pipeline.

</td>
<td width="50%" valign="top">

### 🧊 Bulletproof Deduplication
Redis-backed atomic locks (`SET NX` + 7-day TTL) guarantee an email is never processed twice, even across retries, replays, or multiple running instances.

### ⏰ Self-Healing Watch Subscriptions
Gmail watch channels expire after 7 days — an `APScheduler` background job silently renews all three every 6 days, so the pipeline never goes dark.

### 📦 Container-Native
Single `Dockerfile`, single `uvicorn` process — deploy anywhere that runs containers, point Pub/Sub at the public URL, done.

</td>
</tr>
</table>

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **API / Webhook server** | FastAPI + Uvicorn |
| **Agent orchestration** | LangGraph (`StateGraph`) |
| **LLM** | OpenAI `gpt-4.1-mini` via `langchain-openai` |
| **Email source** | Gmail API + Google Cloud Pub/Sub |
| **State / dedup store** | Redis |
| **Scheduling** | APScheduler (background watch renewal) |
| **Notification channel** | Telegram Bot API |
| **Runtime** | Python 3.13, Docker |

---

## 🚀 Getting Started

### 1. Clone & install
```bash
git clone https://github.com/<you>/CortexMail.git
cd CortexMail
pip install -r requirements.txt
```

### 2. Configure environment
Create a `.env` with:
```env
OPENAI_API_KEY=sk-...
PERSONAL_EMAIL=you@gmail.com
COLLEGE_EMAIL=you@college.edu
WORK_EMAIL=you@org.edu
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
REDIS_URL=redis://...
```

### 3. Authenticate Gmail accounts
Drop OAuth `credentials.json` + per-account `token.json` files under `accounts/`, and mount them as referenced in `main.py` (`/etc/secrets/*_token.json` in production).

### 4. Set up Google Cloud Pub/Sub
Create a Pub/Sub topic, grant `gmail-api-push@system.gserviceaccount.com` publish rights, and point a push subscription at your deployed `/gmail` endpoint.

### 5. Run it
```bash
# Locally
uvicorn main:app --reload

# Or containerized
docker build -t cortexmail .
docker run -p 8000:8000 --env-file .env cortexmail
```

Your inbox is now being watched. 🧠

---

## 🧭 Design Philosophy

> **Triage, don't translate.** CortexMail doesn't try to read every email to you — it filters ruthlessly so the only thing reaching your phone is something that genuinely needs your eyes.

- **Fail loud, fail fast** for Pub/Sub (instant ACK, async processing)
- **Fail silent, fail safe** for noise (low-priority mail is dropped, not stored or surfaced)
- **One node, one job** — each LangGraph node does exactly one thing, making the whole pipeline trivially testable and extensible

---

<div align="center">

### 🧠 Built for people who get too much email and too little time.

*Made with LangGraph, caffeine, and a refusal to read newsletters.*

</div>
