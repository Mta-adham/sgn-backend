# SGN Backend

FastAPI backend for the Saudi Global Network website (member accounts, admin panel,
events, articles, contact, RSVPs, membership applications, Stripe payments).

Runs on **port 8001** (not 8000 — that's used by the unrelated `kite-backend` project
on this machine). `sbn-website`'s `package.json` proxy is already set to
`http://localhost:8001`.

## Quick start

```bash
cp .env.example .env   # defaults already match docker-compose below

docker compose up -d   # starts Postgres on port 5434

python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

alembic upgrade head

python -m app.cli create-admin --email admin@saudiglobal.co --password admin123
python -m app.cli seed           # real SGN events/articles catalog (safe to re-run)
python -m app.cli seed-members   # 30 demo members, development only (safe to re-run)

uvicorn app.main:app --reload --port 8001
```

Check it's alive:

```bash
curl localhost:8001/health
```

## Running the frontend against this backend

In `sbn-website`, `npm start` (port 3000) proxies `/api/*` to this server. Start both:

```bash
# terminal 1
cd sgn-backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8001

# terminal 2
cd sbn-website && npm start
```

Admin panel: `http://localhost:3000/admin`, login with the account created above.
Member login: `http://localhost:3000/members`, using any member an admin creates
(Members tab → Add Member) or a public membership application once you activate it.

## Demo members

`python -m app.cli seed-members` inserts 30 fictional members so the directory,
admin panel and tier gating have realistic data to work against. Every address is on
`example.com`, so this can never be mistaken for the real membership list. They all
share one login password (`sgnmember123` by default, override with `--password`).

The mix is deliberate: all three tiers, every member category, a broad spread of
industries, three members left `active=False` to exercise the admin review queue, and
several with `is_searchable=False` since directory listing is opt-in. Re-running skips
members that already exist, so it never duplicates. **Development only** — do not run
this against production.

## Migrations

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

## Payments (Stripe)

`STRIPE_SECRET_KEY` is empty by default. Without it, `/api/create-payment-intent` and
`/api/create-payment-intent-event` return a clear 503 rather than failing silently, and
the free/basic-tier membership and RSVP paths (which skip Stripe entirely) work with no
configuration. Set `STRIPE_SECRET_KEY` in `.env` to a **test-mode** secret key to enable
paid flows locally — the frontend's Stripe publishable key in `src/Member.js` is
currently a **live** key, so payment testing should not be done against it without
first swapping in a test-mode publishable key too.

## Tests

```bash
pytest
```

## Lint / type-check

```bash
ruff check .
mypy app
```
