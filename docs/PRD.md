# Card Price Viewer PRD

## 1. Product Summary

Card Price Viewer lets a user enter a card name, resolves its Japanese base name from Yugipedia, finds matching Yu-Gi-Oh! OCG listings on Yuyu-tei through a persistent scraper backend, and presents prices in JPY and IDR.

Primary use case: quickly checking the Japanese market price of Yu-Gi-Oh! cards before buying, selling, or comparing rarities.

Deployment constraint: the MVP is split into a static frontend deployed on Vercel and a persistent backend service. It has no serverless function, database, or user account system.

Example:

- Input: `Maxx "C"`
- Yugipedia base name: `増殖するＧ`
- Yuyu-tei query: `https://yuyu-tei.jp/sell/ygo/s/search?search_word=増殖するＧ`

## 2. Goals

- Return useful results from one card-name input.
- Use Yugipedia as the English-to-Japanese name resolver.
- Use Yuyu-tei as the JPY price source through the persistent backend scraper.
- Show each available printing separately by rarity and set/card number.
- Show card/listing images when available.
- Clearly identify sale pricing and availability.
- Convert JPY prices to IDR with the exchange-rate timestamp visible.
- Display results within a few seconds for normal requests.

## 3. Non-Goals for MVP

- Buying cards or managing a cart.
- User accounts, watchlists, alerts, or price history.
- Aggregating additional marketplaces.
- Translating arbitrary card text.
- Guaranteeing that every Yugipedia printing has a Yuyu-tei listing.
- Exact market valuation or investment advice.

## 4. User Flow

1. User enters an English, Japanese, or commonly used card name.
2. User submits with Enter or the Search button.
3. The UI immediately shows a loading state and the submitted name.
4. The server resolves the card on Yugipedia.
5. The client requests an approved Yuyu-tei API, if available, using the Japanese base name, not the localized reading or translated name.
6. Results are normalized, converted to IDR, grouped by printing, and returned.
7. The UI displays the card identity, source timestamps, and listings.
8. Each result links to its Yuyu-tei source page.

If Yugipedia returns multiple possible matches, the UI lists all returned card names and asks the user to choose before requesting prices. If no exact match is available, the backend uses a lightweight YGOPRODeck fuzzy-name query to offer a `Did you mean?` suggestion, but never silently guesses.

## 5. MVP Requirements

### Search

- Required input: card name, 1–100 characters.
- Trim whitespace and reject empty input.
- Support Latin and Japanese characters, punctuation, quotes, and apostrophes.
- Debounce autocomplete only if autocomplete is added; the initial MVP can be submit-driven.
- Cancel or ignore stale responses when the user starts a newer search.
- For ambiguous results, show every candidate returned by Yugipedia and require an explicit selection.
- Paginate large candidate lists and allow loading more results without repeating the price lookup.
- For likely typos, show up to five fuzzy suggestions and label them as suggestions rather than exact matches.
- Show each candidate's Yugipedia card art when available; keep the candidate usable as text when art is missing.
- Exclude Yugipedia pages that are archetypes or other non-card pages; a valid candidate must be a physical card page.
- Exclude candidates labeled as Master Duel, anime, game, or video-game variants.

### Name Resolution

- Fetch the Yugipedia card page or supported search result.
- Extract:
  - canonical Yugipedia title
  - Japanese base name
- card image, when available
- current English card text, when available
  - Yugipedia source URL
- Prefer the `Base` Japanese name, for example `増殖するＧ`, over parenthesized kana readings.
- Preserve the original user input in the response.

### Yuyu-tei Results

For each matching listing, extract when available:

- listing name
- Japanese card name
- set name
- set/card number, such as `STOR-JP086`
- rarity, such as `シークレットレア`
- condition/category only when the source explicitly provides it
- stock state
- regular JPY price
- sale/special JPY price
- whether the listing is on sale
- image URL
- Yuyu-tei listing URL
- source retrieval timestamp

Rules:

- Prefer in-stock listings for the primary result set, but retain an explicit out-of-stock state when the source exposes it.
- Never label a listing “on sale” unless Yuyu-tei provides a sale/special-price signal.
- Do not invent or infer a Cardmarket condition from a source that only exposes stock or damage indicators. Use Cardmarket terms such as Mint, Near Mint, Excellent, Good, Light Played, Played, and Poor only when the source explicitly supplies a compatible condition.
- Keep different rarities, set numbers, and conditions as separate rows.
- Deduplicate only when the source listing identifier or canonical URL is identical.
- Preserve source currency as JPY; do not overwrite the source value with the conversion.

### Currency Conversion

- Convert JPY to IDR using the backend's exchange-rate provider.
- Store the rate used with each response or result batch.
- Display both currencies, for example `¥1,200` and `Rp130,800`.
- Round IDR to the nearest whole rupiah for display.
- Display `1 JPY = X IDR` and the rate timestamp.
- Cache the exchange rate for up to 1 hour; a recent cached rate is preferable to blocking the card lookup.
- If the rate provider fails, show JPY results and a clear “IDR conversion unavailable” state.

### Filtering and Sorting

- Build filter options from the resolved card's actual Yugipedia printing data and matching Yuyu-tei listings.
- Show only rarity options that occur on at least one printing of the current card.
- Use the rarity names defined by the [Yugipedia rarity taxonomy](https://yugipedia.com/wiki/Rarity), while preserving the source's specific rarity label when it is more precise.
- Show only set options that contain at least one printing of the current card.
- Do not show global rarity or set options that are not present on the current card.
- If a selected option produces no valid listings after availability changes, remove it from the active selection and explain why.
- Provide multi-select filters for:
  - rarity
  - set
  - price range
- Price range uses the current source currency, JPY, as the authoritative filter value. IDR is the converted display value and must not produce a different result set because of rounding.
- Price range supports minimum and maximum values and applies to the current price, using the sale price when a listing is on sale.
- Include a “Clear filters” action and show the count of matching listings.
- Filters apply locally to the normalized result set; changing a filter must not trigger another source request.
- Provide sorting for lowest/highest current price, rarity, set, and stock status.
- Preserve active filters and sort order in the URL when practical so a result can be shared or refreshed.

Filter derivation rules:

1. Resolve the card and collect its OCG/printing rarity and set data from Yugipedia.
2. Normalize equivalent labels only when the source explicitly identifies them as equivalent; do not merge distinct rarities such as Secret Rare and Prismatic Secret Rare.
3. Intersect those values with parsed Yuyu-tei listings when building available filter options.
4. Render the remaining unique values in a stable, human-readable order.

If Yugipedia contains a printing but Yuyu-tei has no matching listing, that printing may be shown as card metadata but must not create a selectable price-result filter with zero results.

## 6. Result Presentation

The first screen should contain:

- Search input and submit control.
- Resolved card name: user input plus Japanese base name.
- Main card image, if available.
- Collapsed “Show English text” toggle using the current Yugipedia card text.
- “Last checked” timestamps for Yugipedia, Yuyu-tei, and exchange rate.
- Compact table or responsive cards with:
  - image
  - rarity
  - set/card number
  - set name
  - condition when available and stock
  - IDR price
  - JPY price
  - sale badge and previous/current price when applicable
  - source link

Default sort:

1. In-stock before out-of-stock.
2. On-sale before regular price.
3. Lowest current JPY price first.

Provide filter controls for rarity, set, and price range using only the available options defined above. On mobile, use compact filter controls or a filter sheet, and listing cards are preferred over a horizontally scrolling table.

## 7. Performance Requirements

- Search request target: results visible within 3 seconds at p95 under normal source availability.
- Hard request budget: 5 seconds, after which partial results or a useful error state is shown.
- Fetch Yugipedia, the card metadata fallback, and the exchange rate in parallel where possible.
- Start the Yuyu-tei request as soon as the Japanese base name is known.
- Cache successful name resolutions in the backend for 24 hours.
- Cache normalized Yuyu-tei results in the persistent backend for 2–5 minutes.
- Use per-source timeouts and return partial results instead of waiting indefinitely.
- Do not scrape arbitrary HTML from the browser. The persistent backend owns source requests, CORS, rate limits, and parsing.

Performance acceptance criteria:

- A repeated search served from cache renders in under 500 ms in local production-like testing.
- A cold search displays a loading state immediately and either complete or partial results/error within 5 seconds.
- A slow or unavailable source cannot prevent the other completed source data from rendering.

## 8. Error and Empty States

- Invalid input: “Enter a card name.”
- No Yugipedia match: “Card not found. Check the spelling or try the Japanese name.”
- Ambiguous match: show candidate names and ask for selection.
- Japanese name found, no Yuyu-tei listing: show the resolved name and a source link, then “No matching listings found.”
- Yuyu-tei unavailable: show cached backend results if present, marked with their retrieval time; otherwise show the generated search link and an explicit unavailable-price state.
- Exchange-rate unavailable: show JPY prices and omit converted values rather than using an unmarked fallback.
- Malformed source data: skip only the malformed listing, log the parser error, and return remaining valid listings.

## 9. API Feasibility

### Usable From the Browser

- [Yugipedia MediaWiki API](https://yugipedia.com/api.php?action=help): suitable for title search, page content, and card-page metadata. Its API documentation supports cross-origin requests with `origin=*`. The client still needs to parse the relevant card-page data to obtain the Japanese `Base` name and OCG printings.
- [YGOPRODeck Card API](https://db.ygoprodeck.com/api-guide/): suitable as a fallback for English card identity, card IDs, images, set names, set numbers, rarities, and non-Yuyu-tei market metadata. It is not a replacement for Yuyu-tei JPY pricing or Japanese base-name resolution.
- [Frankfurter API](https://www.frankfurter.app/docs/): suitable for JPY-to-IDR conversion without an API key. Example: `GET https://api.frankfurter.dev/v1/latest?base=JPY&symbols=IDR`. Treat the returned rate as an estimate and show its date.
- [Solomon API](https://github.com/punparin/solomon-api): a community Flask API that scrapes Yuyu-tei and Big Web. Its documented endpoint is `GET /api/cards?name=<Japanese name>&source=yuyutei` and returns JPY price, rarity, condition, set/card ID, and a source URL.

### Yuyu-tei Status

- No documented public Yuyu-tei price API was found during research.
- `https://yuyu-tei.jp/api` currently responds with `403`, so it is not an available public integration endpoint.
- Yuyu-tei's HTML search pages are not a reliable frontend data source: direct browser requests may fail due to CORS, rate limits, or anti-bot controls, and browser-side HTML scraping may conflict with site terms.
- Solomon is a workable community adapter for Yuyu-tei, but it is not a frontend API by itself: it runs Flask/Gunicorn, scrapes Yuyu-tei server-side, and expects Redis-backed caching in its documented setup.
- Solomon's API source does not show CORS middleware, so a separately hosted instance must explicitly allow the Vercel origin before the browser can call it.
- Solomon's current result model is narrower than this product's target model: it does not document images, sale-vs-regular price, or stock status, and its cache is configured for up to three days. These fields must be treated as unavailable unless verified from the deployed instance.
- The chosen MVP mode is a persistent backend service that refactors Solomon's scraper in Python, enables CORS for the Vercel origin, and caches results in memory.
- A generated Yuyu-tei search link remains available as a fallback when the source is unavailable.

## 10. Client Data Shape

The client should normalize all supported API responses into this shape:

```json
{
  "query": "Maxx \"C\"",
  "card": {
    "canonicalName": "Maxx \"C\"",
    "japaneseBaseName": "増殖するＧ",
    "englishText": "...",
    "imageUrl": "https://...",
    "sourceUrl": "https://yugipedia.com/wiki/Maxx_%22C%22"
  },
  "exchangeRate": {
    "base": "JPY",
    "target": "IDR",
    "value": 109.0,
    "retrievedAt": "2026-08-16T00:00:00Z"
  },
  "filters": {
    "rarities": ["Secret Rare", "Ultra Rare"],
    "sets": ["Storm of Ragnarok"],
    "priceJpy": { "min": 100, "max": 50000 }
  },
  "listings": [
    {
      "setName": "...",
      "setNumber": "...",
      "rarity": "...",
      "condition": "...",
      "inStock": true,
      "onSale": false,
      "priceJpy": 1200,
      "salePriceJpy": null,
      "priceIdr": 130800,
      "imageUrl": "https://...",
      "sourceUrl": "https://...",
      "retrievedAt": "2026-08-16T00:00:00Z"
    }
  ],
  "warnings": []
}
```

When Yuyu-tei is unavailable, `listings` may be empty and `warnings` must include the reason plus the generated Yuyu-tei search URL.

## 11. Recommended Stack

- **Vite + vanilla JavaScript/CSS:** instant frontend boot, environment injection, and direct deployment to Vercel.
- **Python + Flask + Requests + BeautifulSoup:** persistent scraper backend, refactoring Solomon's approach against the current Yuyu-tei markup without serverless cold starts.
- **Native browser `fetch`:** frontend-to-backend requests; no frontend HTTP dependency.
- **In-memory cache:** five-minute backend cache for the first deployment; add Redis only when multiple backend instances need shared cache.
- **Python's built-in assertions or pytest:** parser and filtering tests.
- **Vercel:** static frontend hosting. Deploy the backend as a long-running container or VPS service, not a Vercel Function.

Client implementation rules:

- Use `AbortController` for backend request timeouts and stale-search cancellation.
- Run independent backend requests with `Promise.allSettled` so one source failure does not hide completed data.
- Keep source adapters as plain backend functions such as `resolveCard`, `fetchYuyuTei`, and `exchangeRate`; keep frontend filtering local.
- Perform rarity/set filter derivation after normalization and before rendering.
- Use a small backend cache key based on normalized card name and include source retrieval times in the UI.
- Respect each API's rate limits, attribution requirements, CORS policy, and terms of service.

## 12. Technical Approach

- Use Yugipedia MediaWiki API as the primary name and printing metadata source.
- Use YGOPRODeck only as a fallback when Yugipedia search or card-page parsing cannot resolve a usable card identity.
- Use Frankfurter for the JPY/IDR rate, with a one-hour backend cache.
- Use the Python implementation in `backend/app.py` to resolve Yugipedia, scrape Yuyu-tei, normalize listings, and expose `/api/card-price`.
- Configure `FRONTEND_ORIGIN` on the backend so only the deployed frontend can call it.
- Treat Solomon's sale status, stock status, and image fields as unavailable unless the deployed API demonstrably adds them.
- Do not add serverless functions or a database. Server-side HTML scraping is intentional and isolated in the persistent backend.
- Add fixture-based parser tests using representative Yugipedia/API payloads, including multiple rarities, missing images, ambiguous matches, and malformed listings.
- Respect robots.txt, terms of service, reasonable request rates, and source attribution requirements. Do not bypass CAPTCHAs, authentication, or anti-bot controls.

## 13. Success Metrics

- Search completion rate: at least 95% of valid searches return either listings or an explicit no-results state.
- Cold-search p95 under 3 seconds when both sources respond within their timeout budgets.
- Cached-search p95 under 500 ms.
- Parser failure rate below 1% of fetched source pages after launch monitoring.
- Users can identify the cheapest in-stock printing and its source within 10 seconds of opening the result.

## 14. MVP Acceptance Criteria

- Searching `Maxx "C"` resolves and displays `増殖するＧ`.
- An ambiguous query lists candidate card names before any Yuyu-tei price request.
- Broad searches such as `goblin` can load additional physical-card candidates page by page.
- A typo such as `Fidraulys` suggests `Fydraulis Harmonia` and requires the user to select it.
- Searching `Labrynth` does not show the archetype page or Master Duel/game/anime variants.
- When a card's English and Japanese names differ, the card header uses the English name and shows the Japanese base name separately.
- The backend generates a Yuyu-tei search URL with the URL-encoded Japanese base name and exposes normalized results to the frontend.
- The frontend deploys statically to Vercel and calls the persistent backend without a Vercel Function or database.
- The backend returns Yugipedia metadata, Yuyu-tei prices, and JPY/IDR conversion when sources are available.
- The UI never presents fallback marketplace data as Yuyu-tei data.
- The app shows only rarity filters present in the resolved card's printings and matching listings.
- The app shows only set filters to which the resolved card belongs and that have matching listings.
- Each rarity and set filter can be cleared independently, and one control clears all filters.
- No minimum or maximum JPY inputs are shown; price remains sortable.
- A rarity or set absent from the card page is never shown as a filter option.
- Price range filtering uses the current JPY price, including the sale price when applicable.
- Changing filters or sort order does not make another Yugipedia or Yuyu-tei request.
- At least one result can display rarity, set/card number, JPY price, IDR price, stock, and source URL when those fields exist on the source page.
- The card header can reveal the current English card text from Yugipedia.
- Selecting a candidate replaces the search input with that card's English name.
- After a result loads, the masthead contracts so the resolved card and listings receive the visual focus.
- A listing never displays `Play` as a condition unless the source explicitly provides that condition.
- Sale listings show an unambiguous sale indicator and current price.
- Multiple printings are not collapsed into one generic card price.
- Missing images do not break the result row.
- Source failures produce explicit, actionable states.
- The app does not present an IDR value without showing the exchange-rate timestamp.
- A source response exceeding the time budget does not leave the UI spinning indefinitely.

## 15. Future Enhancements

- Support Pokémon and other TCG sources behind the same normalized listing model.
- Search suggestions and recently searched cards.
- Price history and alerts.
- Favorites and collection tracking.
- Additional currencies and user-selected locale.
- Set/rarity filters and a “cheapest available” summary.
- Server-rendered metadata and shareable result URLs.

## 16. Known Risks

- Yuyu-tei and Yugipedia may change markup, rate limits, or access rules.
- Yuyu-tei naming and set-number data may not map one-to-one to Yugipedia printings.
- Scraped prices are time-sensitive and can change between retrieval and purchase.
- Japanese names can be ambiguous or have formatting variants, especially full-width characters and punctuation.
- Exchange-rate conversions are estimates, not payment quotes.

## 17. Source References

- [Yugipedia: Maxx "C"](https://yugipedia.com/wiki/Maxx_%22C%22)
- [Yugipedia MediaWiki API help](https://yugipedia.com/wiki/Special:ApiHelp)
- [YGOPRODeck API guide](https://db.ygoprodeck.com/api-guide/)
- [Frankfurter API documentation](https://www.frankfurter.app/docs/)
- [Yuyu-tei: Japanese name search example](https://yuyu-tei.jp/sell/ygo/s/search?search_word=%E5%A2%97%E6%AE%96%E3%81%99%E3%82%8B%EF%BC%A7)
