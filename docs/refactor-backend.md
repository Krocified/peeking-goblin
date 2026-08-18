# Backend Refactor Plan

Status: implementation started — module extraction complete; final review/deployment verification pending.

## Why

`backend/app.py` is now roughly 700 lines doing 8 jobs in one file:

1. Config/env parsing
2. HTTP client + retry (`get_json`, global `session`)
3. Yugipedia wikitext parsing (`clean_wikitext`, `field`, `parse_sets`, images)
4. Candidate search (ygoprodeck fast path + yugipedia search + `resolve_card`)
5. Yuyu-tei scraper
6. Exchange rate
7. TCG Corner AE catalog + Postgres + probe thread
8. Flask routes + CORS

Plus 3 ad-hoc caches (`cache`, `candidate_cache`, `ae_catalog_cache`), a
Postgres-backed catalog seed workflow, and a warm thread that starts at import
time at the bottom of the file.

### Current correctness issues to fix during the refactor

- `ae_catalog()` can call `refresh_catalog()` while holding the non-reentrant
  `ae_catalog_lock` when the DB row is missing. That path can deadlock instead
  of performing the first catalog fetch.
- A failed initial catalog fetch can leave `aePending` until the next
  maintenance retry. Retry timing and failure state should be explicit.
- The public Shopify feed can return HTTP 429 during pagination. The fetcher
  must retry with backoff and never silently treat a truncated catalog as a
  complete one.
- The catalog seed path (`load_catalog.py`) is operationally important and
  needs to be part of the documented deployment workflow, not an untracked
  one-off script.

## Target layout (11 files, flat, no packages)

```
backend/
  app.py         # Flask app, CORS, routes, background-task startup (~120 lines)
  config.py      # all env constants from lines 17-37 (~40)
  http_client.py # session + get_json/retry (~30)
  cache.py       # one TTLCache class replacing the 3 dict caches (~20)
  wikitext.py    # clean_wikitext, field, parse_sets, card_image_filename, is_physical_card (~85)
  lookup.py      # ygoprodeck_candidates + yugipedia search/canonical + resolve_card (~200)
  yuyutei.py     # Yuyu-tei HTML scraper (~90)
  exchange.py    # exchange_rate + to_idr (~30)
  db.py          # Postgres connection helper + ae_catalog schema + save/load (~60)
  ae_catalog.py  # TCG Corner fetch/cache + probe loop, uses db.py (~140)
  prices.py      # card_price orchestration + available_filters + fetch_asian_english (~110)
  load_catalog.py # one-off local catalog seed command
```

## What moves where

- **config.py**: every `os.environ.get(...)` constant + `allowed_origins`.
- **http_client.py**: `session`, `get_json` (3x retry + `error` check). Imported by
  every module that hits a remote API.
- **cache.py**: one tiny TTL cache for request results and candidate results.
  Do not force the AE catalog into this abstraction: it has a lock, stale data,
  a DB snapshot, a refresh state, and an invalidation fingerprint.
- **wikitext.py**: pure parsing, no I/O (easy to unit test).
- **lookup.py**: `is_latin_query`, `is_rush_card`, `ygoprodeck_candidates`,
  `page_wikitexts`, `direct_image_urls`, `yugipedia_canonical_candidates`,
  `yugipedia_search_titles`, `all_candidate_cards`, `card_candidates`,
  `resolve_card`. All the name -> canonical-card logic.
- **yuyutei.py**: `price`, `stock_state`, `fetch_yuyutei`. Keep the HTML
  scraper isolated from unrelated sources.
- **exchange.py**: `exchange_rate`, `to_idr`.
- **db.py**: `db_connect` (with the "require"-unless-DSN-says-otherwise SSL
  default), the `ae_catalog` table schema + `db_save_catalog` /
  `db_load_catalog`. Owned by `ae_catalog.py` today; future tables (e.g. cached
  prices) land here instead of hiding in a feature module.
- **ae_catalog.py**: AE regexes, catalog cache + lock, `fetch_full_catalog`,
  `refresh_catalog`, `ae_catalog`, `ae_catalog_ready`, `fetch_asian_english`,
  `ae_maintain_loop`. Persistence delegates to `db.py`.
- **prices.py**: `available_filters`, `card_price` (the orchestration glue).
- **load_catalog.py**: explicit local seed command that fetches the catalog and
  writes the Postgres snapshot. It must not start Flask or the maintenance
  thread when imported.
- **app.py**: `Flask` app, CORS handler, `/health`, and `/api/card-price`.
  Keep background startup compatible with gunicorn: `__main__` is not run by
  gunicorn, so either retain guarded import-time startup or add a gunicorn
  config hook. Do not move the thread only into `if __name__ == "__main__"`.

## Migration order (behavior-preserving, commit per step)

1. **config.py + http.py** — pure moves, no logic change. Smoke-test `/health`
   + one search.
2. **cache.py** — add TTLCache for request/candidate results only. Keep the AE
   catalog state explicit. Small, verifiable.
3. **wikitext.py** — pure move.
4. **lookup.py** — move candidate + resolve logic.
5. **yuyutei.py + exchange.py** — move external source code.
6. **db.py** — move connection/schema/read/write code; initialize the table
   once, not inside every catalog write.
7. **ae_catalog.py** — move catalog + refresh state + invalidation loop. Fix
   the DB-miss lock path before moving on.
8. **prices.py** — move orchestration.
9. **app.py** — slim down to routes + CORS + background startup.
10. **load_catalog.py + deployment docs** — document External URL for the
    local seed command and Internal URL for the Render service.
11. **Delete app.py's old body**; verify full flow locally + deploy.

## Deliberately NOT doing (YAGNI)

- No classes/service layer — flat functions, same as now, just organized. No
  DI, no interfaces.
- No `httpx`/async — keeping `requests`. Refactor != stack change.
- No full test suite — add focused tests for parsing, candidate canonicalization,
  AE title parsing, cache expiry, DB round-trip, refresh failure/retry, and the
  API smoke path. The catalog seed command gets one dry-run/DB integration
  check.
- No data-model expansion — Postgres stays a single JSONB catalog row for now,
  but table creation/schema ownership moves to `db.py`.
- No API contract changes — `/api/card-price` responses stay semantically
  compatible. Do not promise byte-identical JSON ordering.
- No price-cache persistence — Yuyu-tei results remain the existing short TTL
  request cache; only the AE catalog is durable.

## Risks

- Import cycles are the main structural hazard — enforce the dependency
  direction: `config`/`http`/`wikitext` at the bottom; source modules above
  them; `ae_catalog`/`prices` above sources; `app` at the top. `load_catalog`
  may import `ae_catalog`, but `ae_catalog` must never import the CLI.
- The import-time warm thread moving into app.py's startup must keep running
  under gunicorn's single worker (current `WARM_AE` guard stays).
- `db_connect`'s SSL default ("require" unless DSN says otherwise) must survive
  the move.
- Render deployment needs two different connection contexts: the local seed
  command uses the **External Database URL**; the Render service uses the
  **Internal Database URL**.
- The database password was exposed during troubleshooting and should be
  rotated before treating this deployment as production.
