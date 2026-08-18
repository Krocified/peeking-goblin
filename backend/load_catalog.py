"""Fetch the full AE catalog locally and push it to Postgres.

Useful when Render's IP is rate-limited by TCG Corner: fetch here (fast, no
429s), push to the DB, and the running app hydrates from the DB on boot.

Usage:
    DATABASE_URL='postgresql://...' python load_catalog.py
"""
import os

os.environ.setdefault("WARM_AE", "0")  # don't start the app's background loop

from ae_catalog import fetch_full_catalog  # noqa: E402
from config import DATABASE_URL  # noqa: E402
from db import save_catalog  # noqa: E402


def main():
    if not DATABASE_URL:
        raise SystemExit("Set DATABASE_URL (Render External Database URL) first")
    print("Fetching full catalog...", flush=True)
    catalog, max_published = fetch_full_catalog()
    print(f"Got {len(catalog)} AE cards; pushing to DB...", flush=True)
    save_catalog(catalog, max_published)
    print(f"Done. max_published={max_published}", flush=True)


if __name__ == "__main__":
    main()
