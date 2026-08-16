# peeking-goblin
Easily peek and check the prices of Yu-Gi-Oh! OCG cards. Search an English card name, resolve it to its Japanese base name, and pull live Yuyu-tei listings by printing — with IDR conversion.

## How it works
1. Search an English card name.
2. Candidates are resolved via YGOPRODeck / Yugipedia (multiple matches show a picker; a single match skips straight to results).
3. The resolved card's Japanese base name is normalized (full-width → half-width) and searched on Yuyu-tei.
4. Listings are parsed with set, rarity, price (JPY + IDR via exchange rate), and stock state.

## Run locally

Backend (Flask):

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Frontend (Vite + React):

```bash
cd frontend
npm install
npm run dev
```

Or use `./run.sh` to start both.

Configuration lives in `backend/.env` and `frontend/.env`. Use the matching `.env.example` files when setting up another environment. The frontend uses Vite so `VITE_*` values are injected at build time.

## Deploy (free)

**Backend — Render** (free web service). The Docker image runs gunicorn with a single
worker (keeps the in-memory cache and the AE-catalog warm thread in one process).

1. Push the repo to GitHub.
2. In Render → New → Blueprint, point at the repo — `render.yaml` is included — or
   create a Web Service manually:
   - Runtime: Docker, Dockerfile: `backend/Dockerfile`
   - Health check: `/health`
   - Env vars: `FRONTEND_ORIGINS` = your frontend URL
3. Render free tier sleeps after ~15 min idle. A free UptimeRobot HTTP check every 5
   min against `/health` keeps it awake.
4. Note the URL, e.g. `https://peeking-goblin-backend.onrender.com`.

**Frontend — Vercel** (free):

1. Push the repo to GitHub, then import it in Vercel.
2. Set the framework preset to **Vite** and add the env var:
   `VITE_API_BASE_URL=https://peeking-goblin-backend.onrender.com`
   (Vercel injects `VITE_*` at build time automatically.)
3. Deploy. The built `dist/` is served by Vercel's CDN.

The frontend is a static SPA; it only *calls* the backend, it doesn't serve it, so the
two live on different free hosts.

## Frontend structure
```
frontend/src/
  main.tsx                 # bootstrap
  types.ts                 # shared types, money formatter, API base
  styles.scss              # resets + shared styles (status, spinner, loading bar)
  styles/_tokens.scss      # color palette (sampled from assets/peeking.jpg)
  components/
    App/                   # state + search logic + layout
    Brand/                 # header (click to go home in compact view)
    SearchForm/
    CandidatePicker/       # ambiguous-match picker + pagination
    PriceResults/          # card header, filters/sort, listings (+ Filter)
    ImageDialog/           # card image preview modal
```
Each component folder holds its component and its `.scss` (minimal, token-based).

## Features
- Single-match auto-resolve (no pointless ambiguity screen)
- Rarity/set filters (dropdowns with per-field clear), sorting
- Out-of-stock chips, sale indicators, JPY/IDR prices
- Loading states: top progress bar, inline spinner, disabled controls
- Asian English prices via TCG Corner (opt-in toggle), USD→IDR conversion, JP/AE source filter
- Mobile-responsive
