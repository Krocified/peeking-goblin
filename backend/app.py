import os
import re
import threading
import time
import unicodedata
from difflib import SequenceMatcher
from urllib.parse import quote, urlencode

import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
session = requests.Session()
session.headers.update({"User-Agent": os.environ.get("USER_AGENT", "card-price-viewer/1.0")})
cache = {}
candidate_cache = {}
PORT = int(os.environ.get("PORT", 8787))
CACHE_SECONDS = int(os.environ.get("CACHE_SECONDS", 300))
REQUEST_TIMEOUT_SECONDS = int(os.environ.get("REQUEST_TIMEOUT_SECONDS", 12))
YUGIPEDIA_API_URL = os.environ.get("YUGIPEDIA_API_URL", "https://yugipedia.com/api.php")
YGOPRODECK_API_URL = os.environ.get("YGOPRODECK_API_URL", "https://db.ygoprodeck.com/api/v7/cardinfo.php")
YUYUTEI_SEARCH_URL = os.environ.get("YUYUTEI_SEARCH_URL", "https://yuyu-tei.jp/sell/ygo/s/search")
TCG_CORNER_COLLECTION_URL = os.environ.get("TCG_CORNER_COLLECTION_URL", "https://tcg-corner.com/collections/yu-gi-oh-single-card-asia-english/products.json")
AE_CATALOG_CACHE_SECONDS = int(os.environ.get("AE_CATALOG_CACHE_SECONDS", 6 * 3600))
EXCHANGE_RATE_URL = os.environ.get("EXCHANGE_RATE_URL", "https://api.frankfurter.dev/v1/latest")
CANDIDATE_PAGE_SIZE = int(os.environ.get("CANDIDATE_PAGE_SIZE", 20))
CANDIDATE_CACHE_SECONDS = int(os.environ.get("CANDIDATE_CACHE_SECONDS", 1800))
allowed_origins = {
    origin.strip()
    for origin in os.environ.get("FRONTEND_ORIGINS", "*").split(",")
    if origin.strip()
}


def get_json(url, params):
    for attempt in range(3):
        response = session.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        result = response.json()
        if "error" not in result:
            return result
        if attempt < 2:
            time.sleep(0.25 * (attempt + 1))
    raise requests.RequestException(result["error"].get("info", "Remote API error"))


def clean_wikitext(value):
    value = re.sub(r"\{\{Ruby\|([^|}]+)\|[^}]+\}\}", r"\1", value)
    value = re.sub(r"\{\{[^{}]+\}\}", "", value)
    value = re.sub(r"\[\[([^|\]]+)\|?[^\]]*\]\]", r"\1", value)
    return re.sub(r"<[^>]+>", "", value).strip()


def field(wikitext, name):
    match = re.search(
        rf"\| {re.escape(name)}\s*=(.*?)(?=\n\| [a-z_]+\s*=|\n\}}\}})",
        wikitext,
        flags=re.S,
    )
    return match.group(1).strip() if match else ""


def parse_sets(wikitext):
    sets = []
    for line in field(wikitext, "jp_sets").splitlines():
        parts = [clean_wikitext(part) for part in line.split(";")]
        if len(parts) < 3 or not parts[0]:
            continue
        sets.append({
            "setNumber": parts[0],
            "setName": parts[1],
            "rarities": [rarity.strip() for rarity in parts[2].split(",") if rarity.strip()],
        })
    return sets


def parse_card_image(wikitext):
    filename = card_image_filename(wikitext)
    return "https://yugipedia.com/wiki/Special:FilePath/" + quote(filename) if filename else None


def card_image_filename(wikitext):
    current = field(wikitext, "current_image")
    fallback = None
    for line in field(wikitext, "image").splitlines():
        parts = [part.strip() for part in line.split(";")]
        if len(parts) == 1 and parts[0]:
            fallback = parts[0]
            continue
        if len(parts) > 1 and parts[1] and fallback is None:
            fallback = parts[1]
        if len(parts) > 1 and parts[0] == current and parts[1]:
            return parts[1]
    return fallback


def is_latin_query(name):
    return any(char.isascii() and char.isalpha() for char in name)


def is_rush_card(card):
    sets = card.get("card_sets") or []
    return bool(sets) and all(
        set_info.get("set_code", "").upper().startswith("RD")
        or "rush" in set_info.get("set_name", "").lower()
        for set_info in sets
    )


def ygoprodeck_candidates(name):
    token = re.split(r"\s+", name.strip())[0]
    queries = [token[:length] for length in range(min(len(token), 8), 3, -1)]
    queries.insert(0, name)
    matches = {}
    for query in queries:
        try:
            result = get_json(YGOPRODECK_API_URL, {"fname": query})
        except requests.RequestException:
            continue
        for card in result.get("data", []):
            card_name = card.get("name")
            if card_name and not is_rush_card(card):
                matches[card_name] = {
                    "name": card_name,
                    "source": "ygoprodeck",
                    "imageUrl": (card.get("card_images") or [{}])[0].get("image_url_small"),
                    "score": SequenceMatcher(None, name.lower(), card_name.lower()).ratio(),
                }
        if matches:
            break
    candidates = list(matches.values())
    if query != name:
        candidates = [candidate for candidate in candidates if candidate["score"] >= 0.45][:5]
    for candidate in candidates:
        candidate.pop("score", None)
    return sorted(candidates, key=lambda item: item["name"].casefold())


def page_wikitexts(titles):
    if not titles:
        return {}
    result = get_json(YUGIPEDIA_API_URL, {
        "action": "query",
        "prop": "revisions",
        "rvprop": "content",
        "format": "json",
        "titles": "|".join(titles),
    })
    pages = {}
    for page in result.get("query", {}).get("pages", {}).values():
        revision = (page.get("revisions") or [{}])[0]
        pages[page.get("title", "")] = revision.get("*", "")
    return pages


def direct_image_urls(filenames):
    filenames = {filename for filename in filenames if filename}
    if not filenames:
        return {}
    result = get_json(YUGIPEDIA_API_URL, {
        "action": "query",
        "prop": "imageinfo",
        "iiprop": "url",
        "format": "json",
        "titles": "|".join(f"File:{filename}" for filename in filenames),
    })
    urls_by_filename = {}
    for page in result.get("query", {}).get("pages", {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        if info.get("url"):
            urls_by_filename[page.get("title", "").removeprefix("File:")] = info["url"]
    return urls_by_filename


def is_physical_card(title, wikitext):
    non_card_variant = re.search(r"\((master duel|anime|game|video game)\)", title, flags=re.I)
    return (
        not non_card_variant
        and "{{CardTable2" in wikitext
        and bool(field(wikitext, "jp_sets").strip())
        and not field(wikitext, "rush_sets").strip()
    )


def yugipedia_search_titles(name, offset):
    search = get_json(YUGIPEDIA_API_URL, {
        "action": "query",
        "list": "search",
        "srsearch": name,
        "srnamespace": 0,
        "srlimit": CANDIDATE_PAGE_SIZE,
        "sroffset": offset,
        "format": "json",
    })
    return (
        [item["title"] for item in search.get("query", {}).get("search", [])],
        search.get("continue", {}).get("sroffset"),
    )


def all_candidate_cards(name):
    key = name.strip().lower()
    cached = candidate_cache.get(key)
    if cached and cached["expires"] > time.time():
        return cached["value"]

    if is_latin_query(name):
        fast_candidates = ygoprodeck_candidates(name)
        if fast_candidates:
            candidate_cache[key] = {"expires": time.time() + CANDIDATE_CACHE_SECONDS, "value": fast_candidates}
            return fast_candidates

    catalog = []
    offset = 0
    while True:
        page_titles, next_page_offset = yugipedia_search_titles(name, offset)
        pages = page_wikitexts(page_titles)
        catalog.extend(
            {"name": title, "source": "yugipedia", "imageFilename": card_image_filename(pages.get(title, ""))}
            for title in page_titles
            if is_physical_card(title, pages.get(title, ""))
        )

        if next_page_offset is None:
            break
        offset = next_page_offset

    if not catalog and is_latin_query(name):
        catalog = [{**candidate, "imageFilename": None} for candidate in ygoprodeck_candidates(name)]

    unique = {item["name"].casefold(): item for item in catalog}
    catalog = sorted(unique.values(), key=lambda item: item["name"].casefold())
    candidate_cache[key] = {"expires": time.time() + CANDIDATE_CACHE_SECONDS, "value": catalog}
    return catalog


def card_candidates(name, page=0):
    catalog = all_candidate_cards(name)
    start = page * CANDIDATE_PAGE_SIZE
    items = catalog[start:start + CANDIDATE_PAGE_SIZE]
    image_urls = direct_image_urls(item.get("imageFilename") for item in items)
    candidates = [
        {**item, "imageUrl": image_urls.get(item.get("imageFilename")) or (
            "https://yugipedia.com/wiki/Special:FilePath/" + quote(item["imageFilename"])
            if item.get("imageFilename") else item.get("imageUrl")
        )}
        for item in items
    ]
    for item in candidates:
        item.pop("imageFilename", None)
    total = len(catalog)
    return candidates, {
        "page": page,
        "pageSize": CANDIDATE_PAGE_SIZE,
        "total": total,
        "totalPages": (total + CANDIDATE_PAGE_SIZE - 1) // CANDIDATE_PAGE_SIZE,
        "hasPrevious": page > 0,
        "hasMore": start + CANDIDATE_PAGE_SIZE < total,
    }


def resolve_card(name, selected_title=None, page=0, candidates_only=False):
    candidates, pagination = card_candidates(name, page) if not selected_title else ([], None)
    title = selected_title or (
        candidates[0]["name"]
        if len(candidates) == 1 and candidates[0]["source"] == "yugipedia" and not candidates_only
        else None
    )
    if not title:
        return {"selectionRequired": True, "query": name, "candidates": candidates, "pagination": pagination}

    page = get_json(YUGIPEDIA_API_URL, {
        "action": "parse",
        "page": title,
        "prop": "wikitext",
        "format": "json",
    })
    parsed = page.get("parse", {})
    wikitext = parsed.get("wikitext", {}).get("*", "")
    japanese_name = clean_wikitext(field(wikitext, "ja_name"))
    if not japanese_name:
        raise ValueError("Japanese base name not found")
    english_name = clean_wikitext(field(wikitext, "en_name")) or parsed.get("title", title)
    return {
        "selectionRequired": False,
        "resolvedTitle": parsed.get("title", title),
        "canonicalName": english_name,
        "japaneseBaseName": japanese_name,
        "englishText": clean_wikitext(field(wikitext, "text")),
        "imageUrl": parse_card_image(wikitext),
        "sets": parse_sets(wikitext),
        "sourceUrl": "https://yugipedia.com/wiki/" + quote(parsed.get("title", title).replace(" ", "_")),
    }


def price(text):
    match = re.search(r"[\d,]+", text or "")
    return int(match.group(0).replace(",", "")) if match else None


def stock_state(product):
    value = product.select_one(".cart_sell_zaiko")
    text = value.get_text(" ", strip=True) if value else ""
    return {
        "inStock": "×" not in text,
        "stockText": text.replace("在庫 :", "").strip(),
    }


def fetch_yuyutei(japanese_name, card_sets):
    # ponytail: NFKC flattens full-width "Ｄ－ＨＥＲＯ" to "D-HERO"; Yuyu-tei only matches half-width
    japanese_name = unicodedata.normalize("NFKC", japanese_name).replace("\u2010", "-")
    last_error = None
    for attempt in range(3):
        try:
            response = session.get(YUYUTEI_SEARCH_URL, params={"search_word": japanese_name}, timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            break
        except requests.RequestException as error:
            last_error = error
            session.close()  # drop poisoned keep-alive connections
            time.sleep(1 + attempt)
    else:
        raise last_error
    soup = BeautifulSoup(response.text, "html.parser")
    listings = []

    for group in soup.select("#card-list3.cards-list"):
        heading = group.select_one("h3")
        rarity = heading.get_text(" ", strip=True).replace("Card List", "").strip() if heading else None
        for product in group.select(".card-product"):
            number_node = product.select_one("span.d-block.border")
            price_node = product.select_one("strong")
            set_number = number_node.get_text(strip=True) if number_node else ""
            current_price = price(price_node.get_text(" ", strip=True) if price_node else "")
            if not set_number or current_price is None:
                continue
            old_price_node = product.select_one("del")
            set_info = next((item for item in card_sets if item["setNumber"] == set_number), {})
            stock = stock_state(product)
            href_node = product.select_one("a[href]")
            image_node = product.select_one(".product-img img")
            source_url = href_node.get("href") if href_node else url
            if source_url and source_url.startswith("/"):
                source_url = YUYUTEI_SEARCH_URL.split("/sell/")[0] + source_url
            old_price = price(old_price_node.get_text(" ", strip=True)) if old_price_node else None
            listings.append({
                "japaneseName": japanese_name,
                "source": "yuyutei",
                "currency": "JPY",
                "setNumber": set_number,
                "setName": set_info.get("setName"),
                "rarity": rarity or (set_info.get("rarities") or [None])[0],
                "condition": None,
                "priceJpy": current_price,
                "salePriceJpy": current_price if old_price else None,
                "regularPriceJpy": old_price,
                "onSale": bool(old_price),
                "inStock": stock["inStock"],
                "stockText": stock["stockText"],
                "imageUrl": image_node.get("src") if image_node else None,
                "sourceUrl": source_url,
            })
    return listings


def exchange_rate():
    # rates[currency] = IDR per 1 unit of currency; add symbols here to support more sources
    result = get_json(EXCHANGE_RATE_URL, {"base": "IDR", "symbols": "JPY,USD"})
    rates = {currency: 1 / value for currency, value in result["rates"].items()}
    return {
        "base": "IDR",
        "target": "IDR",
        "rates": rates,
        "retrievedAt": result["date"],
    }


AE_SET_NUMBER = re.compile(r"^.+-AE.{3}$")
AE_TITLE = re.compile(r"^(?P<setNumber>\S+)\s+(?P<name>.*?)\s*\((?P<rarity>[^()]*)\)(?:\s*\((?P<condition>[^()]*)\))?$")

ae_catalog_cache = {"expires": 0, "value": None}
ae_catalog_lock = threading.Lock()


def ae_catalog_ready():
    return ae_catalog_cache["value"] is not None and ae_catalog_cache["expires"] > time.time()


def ae_catalog():
    if ae_catalog_ready():
        return ae_catalog_cache["value"]
    with ae_catalog_lock:
        if ae_catalog_ready():  # another thread warmed it while we waited
            return ae_catalog_cache["value"]
        catalog = []
        page = 1
        while page <= 40:  # ponytail: Shopify hard-caps around page 40; ~7.3k products at 250/page fits
            try:
                body = get_json(TCG_CORNER_COLLECTION_URL, {"limit": 250, "page": page})
            except requests.RequestException as error:
                if page > 1 and error.response is not None and error.response.status_code == 429:
                    break  # rate-limited past the end of the catalog
                raise
            products = body.get("products", [])
            if not products:
                break
            for product in products:
                match = AE_TITLE.match(product.get("title", ""))
                if not match:
                    continue
                set_number = match.group("setNumber")
                if not AE_SET_NUMBER.match(set_number):
                    continue
                variant = (product.get("variants") or [{}])[0]
                catalog.append({
                    "name": match.group("name"),
                    "setNumber": set_number,
                    "rarity": match.group("rarity") or None,
                    "condition": match.group("condition") or None,
                    "priceUsd": float(variant.get("price") or 0),
                    "inStock": bool(variant.get("available")),
                    "imageUrl": (product.get("images") or [{}])[0].get("src"),
                    "sourceUrl": f"https://tcg-corner.com/products/{product.get('handle', '')}",
                })
            page += 1
            time.sleep(1.0)  # ponytail: politeness delay; Shopify 429s aggressive pagers
        ae_catalog_cache["value"] = catalog
    ae_catalog_cache["expires"] = time.time() + AE_CATALOG_CACHE_SECONDS
    return catalog


def to_idr(price, currency, rates):
    if price is None or not rates or currency not in rates:
        return None
    return round(price * rates[currency])


def fetch_asian_english(canonical_name, rates):
    listings = []
    lowered = canonical_name.strip().lower()
    for item in ae_catalog():
        if lowered != item["name"].strip().lower():
            score = SequenceMatcher(None, lowered, item["name"].strip().lower()).ratio()
            if score < 0.85:
                continue
        listings.append({
            **item,
            "source": "tcg-corner",
            "currency": "USD",
            "priceJpy": None,
            "priceIdr": to_idr(item["priceUsd"], "USD", rates),
            "onSale": None,
            "stockText": None,
            "sourceUrl": item["sourceUrl"],
        })
    return listings


def available_filters(listings):
    prices = [item["priceJpy"] for item in listings if item.get("priceJpy") is not None]
    return {
        "rarities": sorted({item["rarity"] for item in listings if item.get("rarity")}),
        "sets": sorted({item["setName"] for item in listings if item.get("setName")}),
        "priceJpy": {"min": min(prices, default=0), "max": max(prices, default=0)},
    }


def card_price(name, selected_title=None, page=0, candidates_only=False, include_ae=False):
    key = f"{name.strip().lower()}::{(selected_title or '').lower()}::ae={int(include_ae)}"
    ae_pending = False
    if candidates_only or page:
        return resolve_card(name, selected_title, page, candidates_only)
    cached = cache.get(key)
    if cached and cached["expires"] > time.time():
        return cached["value"]

    card = resolve_card(name, selected_title, page, candidates_only)
    if card.get("selectionRequired"):
        return card
    warnings = []
    try:
        listings = fetch_yuyutei(card["japaneseBaseName"], card["sets"])
    except requests.RequestException as error:
        listings = []
        print(f"Yuyu-tei fetch failed after retries: {error!r}")
        warnings.append("Yuyu-tei is unreachable right now — prices could not be fetched. Try again in a moment.")
    try:
        rate = exchange_rate()
    except requests.RequestException:
        rate = None
        warnings.append("IDR conversion unavailable")

    for listing in listings:
        listing["priceIdr"] = to_idr(listing["priceJpy"], "JPY", rate["rates"] if rate else None)
    if include_ae:
        if ae_catalog_ready():
            try:
                listings.extend(fetch_asian_english(card["canonicalName"], rate["rates"] if rate else None))
            except requests.RequestException as error:
                print(f"TCG Corner fetch failed: {error!r}")
                warnings.append("Asian English prices unavailable right now. Try again in a moment.")
        else:
            ae_pending = True
            warnings.append("Asian English prices are still loading — they'll appear in a moment.")
    result = {
        "query": name,
        "aePending": ae_pending,
        "card": card,
        "exchangeRate": rate,
        "filters": available_filters(listings),
        "listings": listings,
        "warnings": warnings,
        "yuyuteiSearchUrl": YUYUTEI_SEARCH_URL + "?" + urlencode({"search_word": unicodedata.normalize("NFKC", card["japaneseBaseName"]).replace("\u2010", "-")}),
        "tcgCornerSearchUrl": "https://tcg-corner.com/search?" + urlencode({"q": card["canonicalName"]}),
    }
    if not ae_pending:  # don't cache an incomplete result; the client refetches when AE lands
        cache[key] = {"expires": time.time() + CACHE_SECONDS, "value": result}
    return result


@app.after_request
def cors(response):
    origin = (request.headers.get("Origin") or "").rstrip("/")
    allowed = {item.rstrip("/") for item in allowed_origins}
    if "*" in allowed:
        allow = "*"
    elif origin in allowed:
        allow = origin
    else:
        allow = "null"
    response.headers["Access-Control-Allow-Origin"] = allow
    response.headers["Vary"] = "Origin"
    return response


@app.get("/health")
def health():
    return jsonify(ok=True)


@app.get("/api/card-price")
def api_card_price():
    name = request.args.get("name", "").strip()
    selected_title = request.args.get("title", "").strip() or None
    try:
        page = max(0, int(request.args.get("page", 0)))
    except ValueError:
        return jsonify(error="Invalid candidate offset"), 400
    candidates_only = request.args.get("candidates_only") == "1"
    include_ae = request.args.get("include_ae") == "1"
    if len(name) < 3:
        return jsonify(error="Enter at least 3 characters"), 400
    if len(name) > 100:
        return jsonify(error="Card name must be 100 characters or fewer"), 400
    try:
        return jsonify(card_price(name, selected_title, page, candidates_only, include_ae))
    except (requests.RequestException, ValueError) as error:
        return jsonify(error=str(error)), 502


# ponytail: warm AE catalog on import so the gunicorn worker is ready before first request;
# storefront search can't find singles, so the 30s catalog fetch happens in the background
if os.environ.get("WARM_AE", "1") != "0":
    threading.Thread(target=ae_catalog, daemon=True).start()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
