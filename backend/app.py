import os
import re
import time
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
PORT = int(os.environ.get("PORT", 8787))
CACHE_SECONDS = int(os.environ.get("CACHE_SECONDS", 300))
REQUEST_TIMEOUT_SECONDS = int(os.environ.get("REQUEST_TIMEOUT_SECONDS", 12))
YUGIPEDIA_API_URL = os.environ.get("YUGIPEDIA_API_URL", "https://yugipedia.com/api.php")
YGOPRODECK_API_URL = os.environ.get("YGOPRODECK_API_URL", "https://db.ygoprodeck.com/api/v7/cardinfo.php")
YUYUTEI_SEARCH_URL = os.environ.get("YUYUTEI_SEARCH_URL", "https://yuyu-tei.jp/sell/ygo/s/search")
EXCHANGE_RATE_URL = os.environ.get("EXCHANGE_RATE_URL", "https://api.frankfurter.dev/v1/latest")
CANDIDATE_PAGE_SIZE = int(os.environ.get("CANDIDATE_PAGE_SIZE", 20))
allowed_origins = {
    origin.strip()
    for origin in os.environ.get("FRONTEND_ORIGINS", "*").split(",")
    if origin.strip()
}


def get_json(url, params):
    response = session.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()


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


def fuzzy_names(name):
    token = re.split(r"\s+", name.strip())[0]
    queries = [token[:length] for length in range(min(len(token), 8), 3, -1)]
    matches = {}
    for query in queries:
        try:
            result = get_json(YGOPRODECK_API_URL, {"fname": query})
        except requests.RequestException:
            continue
        for card in result.get("data", []):
            card_name = card.get("name")
            if card_name:
                matches[card_name] = SequenceMatcher(None, name.lower(), card_name.lower()).ratio()
        if matches:
            break
    return [name for name, score in sorted(matches.items(), key=lambda item: item[1], reverse=True) if score >= 0.45][:5]


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


def direct_image_urls(pages):
    filenames = {title: card_image_filename(wikitext) for title, wikitext in pages.items()}
    filenames = {title: filename for title, filename in filenames.items() if filename}
    if not filenames:
        return {}
    result = get_json(YUGIPEDIA_API_URL, {
        "action": "query",
        "prop": "imageinfo",
        "iiprop": "url",
        "format": "json",
        "titles": "|".join(f"File:{filename}" for filename in filenames.values()),
    })
    urls_by_filename = {}
    for page in result.get("query", {}).get("pages", {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        if info.get("url"):
            urls_by_filename[page.get("title", "").removeprefix("File:")] = info["url"]
    return {title: urls_by_filename.get(filename) for title, filename in filenames.items()}


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


def card_candidates(name, offset=0):
    titles = []
    next_offset = offset
    while next_offset is not None and len(titles) < CANDIDATE_PAGE_SIZE:
        page_titles, next_page_offset = yugipedia_search_titles(name, next_offset)
        pages = page_wikitexts(page_titles)
        image_urls = direct_image_urls(pages)
        titles.extend(
            {"name": title, "source": "yugipedia", "imageUrl": image_urls.get(title) or parse_card_image(pages.get(title, ""))}
            for title in page_titles
            if is_physical_card(title, pages.get(title, ""))
        )
        next_offset = next_page_offset

    pagination = {
        "offset": offset,
        "nextOffset": next_offset,
        "hasMore": next_offset is not None,
    }
    if titles:
        return titles, pagination
    if offset:
        return [], pagination
    fuzzy = fuzzy_names(name)
    pages = page_wikitexts(fuzzy)
    image_urls = direct_image_urls(pages)
    return [
        {"name": title, "source": "ygoprodeck", "imageUrl": image_urls.get(title) or parse_card_image(pages.get(title, ""))}
        for title in fuzzy
        if is_physical_card(title, pages.get(title, ""))
    ], {"offset": 0, "nextOffset": None, "hasMore": False}


def resolve_card(name, selected_title=None, offset=0, candidates_only=False):
    candidates, pagination = card_candidates(name, offset) if not selected_title else ([], None)
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
    response = session.get(YUYUTEI_SEARCH_URL, params={"search_word": japanese_name}, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
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
    result = get_json(EXCHANGE_RATE_URL, {"base": "JPY", "symbols": "IDR"})
    return {
        "base": "JPY",
        "target": "IDR",
        "value": result["rates"]["IDR"],
        "retrievedAt": result["date"],
    }


def available_filters(listings):
    prices = [item["priceJpy"] for item in listings]
    return {
        "rarities": sorted({item["rarity"] for item in listings if item.get("rarity")}),
        "sets": sorted({item["setName"] for item in listings if item.get("setName")}),
        "priceJpy": {"min": min(prices, default=0), "max": max(prices, default=0)},
    }


def card_price(name, selected_title=None, offset=0, candidates_only=False):
    key = f"{name.strip().lower()}::{(selected_title or '').lower()}"
    if candidates_only or offset:
        return resolve_card(name, selected_title, offset, candidates_only)
    cached = cache.get(key)
    if cached and cached["expires"] > time.time():
        return cached["value"]

    card = resolve_card(name, selected_title, offset, candidates_only)
    if card.get("selectionRequired"):
        return card
    warnings = []
    try:
        listings = fetch_yuyutei(card["japaneseBaseName"], card["sets"])
    except requests.RequestException as error:
        listings = []
        warnings.append(f"Yuyu-tei unavailable: {error}")
    try:
        rate = exchange_rate()
    except requests.RequestException:
        rate = None
        warnings.append("IDR conversion unavailable")

    for listing in listings:
        listing["priceIdr"] = round(listing["priceJpy"] * rate["value"]) if rate else None
    result = {
        "query": name,
        "card": card,
        "exchangeRate": rate,
        "filters": available_filters(listings),
        "listings": listings,
        "warnings": warnings,
        "yuyuteiSearchUrl": YUYUTEI_SEARCH_URL + "?" + urlencode({"search_word": card["japaneseBaseName"]}),
    }
    cache[key] = {"expires": time.time() + CACHE_SECONDS, "value": result}
    return result


@app.after_request
def cors(response):
    origin = request.headers.get("Origin")
    response.headers["Access-Control-Allow-Origin"] = "*" if "*" in allowed_origins else (
        origin if origin in allowed_origins else next(iter(allowed_origins), "null")
    )
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
        offset = max(0, int(request.args.get("offset", 0)))
    except ValueError:
        return jsonify(error="Invalid candidate offset"), 400
    candidates_only = request.args.get("candidates_only") == "1"
    if len(name) < 3:
        return jsonify(error="Enter at least 3 characters"), 400
    if len(name) > 100:
        return jsonify(error="Card name must be 100 characters or fewer"), 400
    try:
        return jsonify(card_price(name, selected_title, offset, candidates_only))
    except (requests.RequestException, ValueError) as error:
        return jsonify(error=str(error)), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
