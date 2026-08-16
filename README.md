# peeking-goblin
Easily peek and check the prices of cards

## Run locally

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Configuration lives in `backend/.env` and `frontend/.env`. Use the matching `.env.example` files when setting up another environment. The frontend uses Vite so `VITE_*` values are injected at build time.
