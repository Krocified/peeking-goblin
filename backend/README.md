# Card Price Backend

Long-running Python service for the static frontend. It resolves card names with Yugipedia, scrapes Yuyu-tei, converts JPY to IDR, and serves Asian English prices from the Postgres-backed catalog.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Configuration lives in `.env`. Copy `.env.example` when setting up a new environment. Set `FRONTEND_ORIGINS` to a comma-separated list of allowed frontend origins.

To seed the AE catalog from a local machine, use the Render **External Database URL**:

```bash
DATABASE_URL='postgresql://...' .venv/bin/python load_catalog.py
```

The Render service uses the Postgres **Internal Database URL** as `DATABASE_URL`.

The service exposes:

```text
GET /api/card-price?name=Maxx%20%22C%22
GET /health
```

The backend is intentionally persistent, not serverless. Source integrations live in separate modules; `app.py` only owns Flask routes and startup. It uses the current Yuyu-tei search page and should be monitored if the site markup changes.
