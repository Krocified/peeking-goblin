# Card Price Backend

Long-running Python service for the static frontend. It resolves the Japanese card name with Yugipedia, scrapes Yuyu-tei, converts JPY to IDR, and caches results in memory for five minutes.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Configuration lives in `.env`. Copy `.env.example` when setting up a new environment. Set `FRONTEND_ORIGINS` to a comma-separated list of allowed frontend origins.

The service exposes:

```text
GET /api/card-price?name=Maxx%20%22C%22
GET /health
```

The backend is intentionally persistent, not serverless. It uses the current Yuyu-tei search page and should be monitored if the site markup changes.
