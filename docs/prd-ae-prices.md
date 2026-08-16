# PRD: Asian English (AE) price source — TCG Corner

## Status
Proposed. Assessment done; details below.

## Summary
Add https://tcg-corner.com (Shopify store) as a second price source for Asian English
prints, alongside Yuyu-tei (Japanese). Users opt in per search via a toggle.

## Assessment findings (verified 2026-08-16)
- The AE collection exposes a public Shopify `products.json` endpoint:
  `/collections/yu-gi-oh-single-card-asia-english/products.json?limit=250&page=N`
- ~7,436 products, 30 pages @ 250/page. Full catalog fetch ≈ 30 requests (one-time, cached).
- Product title format: `{setNumber} {english card name} ({rarity}) ({Status})`
  e.g. `CR12-AE097 Pressured Planet Wraitsoth (UL) (Status B)`
- Each product: 1 variant, `price` (USD), `available` (bool), `handle` (product URL).
- Prices are USD (store currency confirmed on product pages).
- Card names are English — matches our already-resolved `canonicalName`. No Japanese
  lookup needed.
- The storefront search endpoint is useless for card names (indexes set-level titles);
  local matching over the cached catalog is the right approach.
- Rarity codes are abbreviations (`UL`, `PSER`, `SE`, `N`, …) — shown as-is.

## Non-goals
- No other TCG Corner categories (JP singles, sealed).
- No cart/checkout integration.
- No rarity-code expansion table unless users complain.

## Data flow
1. BE fetches + caches the AE catalog (name, setNumber, rarity, condition, price USD,
   available, URL) with a TTL (proposed 6h; catalog changes slowly).
   Only products whose set number matches the AE pattern `????-AE???` (regex
   `^.+-AE.{3}$`, e.g. `CR12-AE097`, `INFO-AES32`) are kept. Non-AE codes in the
   collection are dropped at ingest.
2. On search with AE enabled, BE fuzzy-matches `canonicalName` against catalog names
   (`SequenceMatcher` ratio ≥ 0.85 or normalized exact match), same approach as
   ygoprodeck candidates.
3. Matched listings are appended to `listings[]` with `source: "tcg-corner"`,
   `currency: "USD"`.
4. IDR conversion for ALL listings regardless of source currency: fetch USD and JPY
   rates against IDR in one frankfurter call (`symbols=IDR,USD` from JPY base gives
   JPY→IDR directly; USD→IDR = IDR-per-JPY ÷ USD-per-JPY). Each listing carries
   `priceIdr` alongside its native `priceJpy`/`priceUsd`.

## API changes
- `GET /api/card-price` gains `include_ae=1`.
- Listing object gains `source: "yuyutei" | "tcg-corner"`, `currency: "JPY" | "USD"`,
  and `priceUsd` (AE rows). `priceIdr` is populated on every listing from its native
  currency.
- `warnings` may carry AE-specific unavailability without failing the whole request
  (same pattern as Yuyu-tei).

## Frontend changes
- Toggle in the search form: "Include Asian English prints" (checkbox, default off).
  Persisted in state only; passed through the search call.
- Listings render in one list with a small source tag (JP / AE) per row; price stack
  shows native currency + IDR per row (JPY+IDR or USD+IDR). Out-of-stock chip reused
  (`available: false`).
- Filters/sort operate on the merged list as today.

## Risks / open questions
- Shopify may rate-limit the 30-page catalog fetch; mitigate with a 0.5s delay between
  pages and the 6h cache. (ponytail: fine until proven otherwise)
- Fuzzy matching may surface near-names (e.g. "Hero" reprints); ≥0.85 threshold plus
  set-number sanity check keeps it quiet. Tune later if noisy.
- Status suffix (`Status B`) is TCG Corner's grading shorthand — display as condition.

## Effort
BE: catalog fetcher + cache (~60 LOC), matcher (~15), API plumb (~10).
FE: toggle + source tag + per-row currency (~30 LOC + styles).
