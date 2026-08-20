# SGN Backend

Backend for the Saudi Global Network website (member accounts, admin panel, events, articles, contact).

## Quick start

```bash
cp .env.example .env

python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

uvicorn app.main:app --reload
```

Check it's alive:

```bash
curl localhost:8000/health
```

The frontend (`sbn-website`) proxies `/api/*` to `http://localhost:8000` in development (see its `package.json`).

## Tests

```bash
pytest
```

## Lint / type-check

```bash
ruff check .
mypy app
```
