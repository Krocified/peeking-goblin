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
- Mobile-responsive
