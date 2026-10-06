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

`tests/test_vocabulary_sync.py` compares the industry and category lists in `app/core/`
against `sbn-website/src/memberCategories.js`. The backend drops values it does not
recognise *silently*, so a sector added to the frontend picker alone would vanish on
save with no error — this test turns that into a failure instead. It skips automatically
if `sbn-website` is not checked out next to this repo.

## Lint / type-check

```bash
ruff check .
mypy app
```

## Going live

The server enforces its own production configuration. With `ENVIRONMENT=production` it
refuses to start if `JWT_SECRET` is still the placeholder or too short, if `CORS_ORIGINS`
contains `*`, or if any origin is plain http. Every problem is listed in one error, so
one restart tells you everything that is wrong.

Start from `.env.production.example`:

```bash
cp .env.production.example .env     # on the server, then fill it in
python -c "import secrets; print(secrets.token_urlsafe(48))"   # JWT_SECRET
```

Then, on the server:

```bash
alembic upgrade head
python -m app.cli create-admin --email you@saudiglobal.co --password '<strong password>'
python -m app.cli seed          # real events/articles catalog
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

Do **not** run `seed-members` in production — it inserts 30 fictional people.

### How the frontend finds the backend in production

This matters more than it looks. `sbn-website` calls the API at the **relative** path
`/api/...` (`const API_BASE = '/api'`), and the `"proxy": "http://localhost:8001"` in its
`package.json` is **only used by `npm start`** — it has no effect on a production build.
So a built frontend sends `/api/*` to whatever host served the page.

That leaves two deployment shapes, and only one of them works as the code stands:

1. **Same origin (works unchanged, recommended.)** One reverse proxy serves the built
   frontend and forwards `/api/*` and `/uploads/*` to this backend. Relative paths resolve
   correctly, and CORS stops mattering because it is no longer cross-origin. Sketch:

   ```nginx
   location /api/     { proxy_pass http://127.0.0.1:8001; }
   location /uploads/ { proxy_pass http://127.0.0.1:8001; }
   location /         { root /var/www/sbn-website/build; try_files $uri /index.html; }
   ```

2. **Separate domains (needs a frontend change.)** If the frontend is on a static host
   (Netlify, Vercel, S3) and the backend on `api.saudiglobal.co`, every `/api/*` call hits
   the static host and 404s. `sbn-website` would need its hardcoded `API_BASE` replaced
   with an env-driven base URL (e.g. `process.env.REACT_APP_API_URL`), applied in all four
   files that define it — `Event.js`, `EventDetail.js`, `Article.js`, `Contact.js` — plus
   the components using literal `/api/...` paths. `CORS_ORIGINS` then has to list the
   frontend's exact https origin.

Option 1 needs no code changes on either side, which is why it is the recommendation.

Still to be decided outside this repo:

- **Hosting and process supervision.** `uvicorn --reload` is a development server. In
  production run it under a supervisor (systemd, Docker with a restart policy, or a
  platform like Railway/Render/Fly) so it comes back after a crash or reboot.
- **TLS and a reverse proxy.** Terminate https in front of the app (nginx, Caddy, or the
  platform's own router). `CORS_ORIGINS` must be https, so the frontend has to be served
  over https too.
- **Managed Postgres.** The `docker-compose.yml` database is for local development: the
  password is `sgn` and the port is published to the host. Use a managed instance with
  automated backups, and confirm a restore actually works before launch.
- **`uploads/` is on local disk.** `POST /api/admin/uploads` writes to a directory served
  as static files, so it does not survive a container rebuild and is not shared between
  instances. Mount a persistent volume, or move to object storage before scaling past one
  instance.
- **Stripe keys must match modes.** A live secret key here requires a live publishable key
  in `sbn-website/src/Member.js`, and vice versa. Mixed modes fail at payment time.
