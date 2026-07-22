# AISHA AI — Backend

FastAPI backend for the AISHA AI WhatsApp sales assistant. Handles WhatsApp webhooks, the AI conversation engine, the marketplace/cart/checkout flow, order tracking, and the business dashboard API.

---

## Tech Stack

| Tool | Purpose |
|---|---|
| FastAPI | Web framework — routes, requests, responses |
| Uvicorn | ASGI server that runs FastAPI |
| SQLAlchemy | ORM — Python objects instead of raw SQL |
| Alembic | Database migrations — version control for the schema |
| PostgreSQL (Neon) | Shared production/dev database |
| psycopg2-binary | PostgreSQL driver |
| python-dotenv | Loads `.env` |
| passlib[bcrypt] | Password hashing |
| python-jose | JWT auth |
| httpx | HTTP client (Twilio, etc.) |
| google-auth | Google OAuth 2.0 |
| redis | Conversation + business prompt caching |
| anthropic | Claude AI SDK |
| google-generativeai | Gemini AI SDK |
| twilio | WhatsApp messaging + Content Templates |

---

## Prerequisites

```bash
python --version      # 3.10 or higher
pip --version
```

---

## First-Time Setup

### 1. Clone and branch

```bash
git clone https://github.com/YOUR-USERNAME/aisha-ai.git
cd aisha-ai
git checkout dev
git pull origin dev
git checkout -b yourname/feature-name
```

### 2. Virtual environment

```bash
cd backend
python3 -m venv venv
source venv/bin/activate       # Windows: source venv\Scripts\activate
```

You'll see `(venv)` at the start of your prompt when it's active. `deactivate` to exit it.

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

Always install from this file, not one-off `pip install`s — it keeps everyone on the same package versions.

### 4. Environment variables

```bash
cp .env.example .env
```

Fill in `.env`:

```dotenv
# Shared Neon database — same one for the whole team. Anything one
# person adds, everyone sees.
DATABASE_URL=postgresql://neondb_owner:*****************?sslmode=require&channel_binding=require
DIRECT_DATABASE_URL=postgresql://neondb_owner:*****************?sslmode=require&channel_binding=require

SECRET_KEY=your-secret-key-here
ANTHROPIC_API_KEY=your-key-here
GEMINI_API_KEY=your-key-here
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_WHATSAPP_NUMBER=your-sandbox-or-production-number
TWILIO_LIST_PICKER_SID=see "Twilio Content Templates" below
TWILIO_QUICK_REPLY_SID=see "Twilio Content Templates" below
TWILIO_BROWSE_MORE_SID=see "Twilio Content Templates" below

BASE_URL=your-public-url   # ngrok URL in dev, real domain in production
```

`.env` is gitignored — never commit it, never hardcode keys in Python files.

- `DATABASE_URL` — used by the running app (FastAPI, Redis-cached queries). Uses the **pooled** Neon connection.
- `DIRECT_DATABASE_URL` — used by Alembic for migrations. Uses the **non-pooled** Neon connection — pooled connections can fail on some DDL operations.

### 5. Run migrations and start the server

```bash
alembic upgrade head
uvicorn main:app --reload
```

The database is already live and shared — you're applying whatever migrations you don't have yet, not creating anything from scratch.

Server runs at `http://localhost:8000`. Check:
- `http://localhost:8000/docs` — interactive API docs, test any endpoint from the browser
- `http://localhost:8000/redoc` — alternate docs view

---

## Folder Structure

```
backend/
├── alembic/               # Migrations — commit everything in versions/
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── app/
│   ├── auth/               # Registration, login, JWT, Google OAuth
│   ├── categories/         # Category CRUD (dashboard)
│   ├── orders/              # Order tracking (dashboard)
│   ├── flows/               # marketplace_flow.py — cart/checkout state machine
│   ├── webhook/             # WhatsApp incoming message handler + Twilio client
│   ├── ai/                  # AI engine, prompts, Redis cache
│   ├── scripts/              # One-off setup scripts (Twilio templates, etc.)
│   ├── database.py
│   ├── models.py
│   └── __init__.py
├── main.py                 # All routers registered here
├── requirements.txt
├── alembic.ini
├── .env                    # Never commit
└── .env.example
```

---

## Database — Shared Neon Instance

Everyone points at the same Postgres database. No local Postgres needed for this project — if you have one from earlier, it's no longer used.

### Rules

- **Never call `Base.metadata.create_all()`** — schema changes only happen through Alembic.
- Every schema change:
  ```bash
  alembic revision --autogenerate -m "short description"
  alembic upgrade head
  ```
- **Commit the generated migration file right after**, so everyone else picks it up on their next `git pull` + `alembic upgrade head`. Migration files live in `alembic/versions/` and are version controlled — never edit a migration that's already been applied and shared.
- If a teammate's changes include a new migration:
  ```bash
  git pull
  alembic upgrade head
  ```

### Everyday commands

```bash
alembic current                              # what revision is the DB on
alembic history                              # full migration chain
alembic revision --autogenerate -m "..."     # generate a new migration
alembic upgrade head                         # apply pending migrations
alembic downgrade -1                         # roll back one step
```

### Checking data directly

```bash
psql "$DIRECT_DATABASE_URL" -c "\dt"          # list tables
psql "$DIRECT_DATABASE_URL" -c "\d orders"    # describe a table
```

Or use Neon's own console (console.neon.tech) — Tables tab for a spreadsheet view, SQL Editor for queries.

### Common errors

**`no schema has been selected to create in`**
Alembic is using the pooled `DATABASE_URL` instead of `DIRECT_DATABASE_URL`. Check `alembic/env.py`'s `get_url()` — it should read `DIRECT_DATABASE_URL`.

**`unsupported startup parameter in options: search_path`**
Same cause, same fix — Alembic needs the direct connection, not the pooler.

**`Can't locate revision identified by '...'`**
Your local migration files are behind the shared history.
```bash
git pull
alembic current
alembic history
```
Don't run `alembic stamp` to force past this — ask first, it can desync your DB from the real migration state.

**`psql` connects to the wrong database**
Always quote and use the direct URL explicitly:
```bash
psql "$DIRECT_DATABASE_URL" -c "\dt"
```

---

## Twilio Content Templates

One-time setup script — run it once per Twilio account (e.g. if the project ever moves to a new Twilio account).

**Before running**, open `app/scripts/create_templates.py` and make sure all three lines are uncommented under `__main__`:
```python
list_sid = create_list_picker_template()
quick_reply_sid = create_quick_reply_template()
browse_more_sid = create_browse_more_template()
```

Requires `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` in `.env` for the target account.

```bash
python app/scripts/create_templates.py
```

**After running**, copy the printed SIDs into `.env`:
```dotenv
TWILIO_LIST_PICKER_SID=<from output>
TWILIO_QUICK_REPLY_SID=<from output>
TWILIO_BROWSE_MORE_SID=<from output>
```

Restart `uvicorn` after updating `.env`.

**Verify a template:**
```bash
curl -X GET "https://content.twilio.com/v1/Content/<SID>" \
  -u "<ACCOUNT_SID>:<AUTH_TOKEN>"
```

---

## Running the Server (every session)

```bash
cd backend
source venv/bin/activate
alembic upgrade head        # pick up any new migrations
uvicorn main:app --reload
```

Two terminals run side by side in development: backend (`uvicorn`, port 8000) and frontend (`npm run dev`, port 5173).

---

## Adding a New Python Package

```bash
pip install package-name
pip freeze > requirements.txt
git add requirements.txt
git commit -m "chore: add package-name dependency"
```

After pulling a teammate's changes that touch `requirements.txt`:
```bash
pip install -r requirements.txt
```

---

## Branch & PR Workflow

```
1. Work on your branch   → git add . && git commit -m "feat: ..."
2. Push your branch      → git push origin yourname/feature-name
3. Open a PR             → base: dev ← compare: yourname/feature-name
4. Teammate reviews and approves
5. Merge into dev
6. Pull dev locally      → git checkout dev && git pull origin dev
7. Run migrations if any → alembic upgrade head
8. Branch off dev again for the next feature
```

Commit message format:
```
feat: add auth registration endpoint
fix: correct JWT expiry bug
chore: update requirements.txt
refactor: move AI logic to dedicated module
docs: update README
```

---

## AI Provider Strategy

The AI engine is swappable via config. Gemini during development (free tier), Claude for demos (better quality). Configured in `app/ai/`.
