import unicodedata
import logging
from urllib.parse import urlencode

import requests

from ae_catalog import ae_catalog_ready, fetch_asian_english
from cache import TTLCache
from config import CACHE_SECONDS, YUYUTEI_SEARCH_URL
from exchange import exchange_rate, to_idr
from lookup import resolve_card
from yuyutei import fetch_yuyutei

cache = TTLCache()
logger = logging.getLogger(__name__)


def available_filters(listings):
    prices = [item["priceJpy"] for item in listings if item.get("priceJpy") is not None]
    return {
        "rarities": sorted({item["rarity"] for item in listings if item.get("rarity")}),
        "sets": sorted({item["setName"] for item in listings if item.get("setName")}),
        "priceJpy": {"min": min(prices, default=0), "max": max(prices, default=0)},
    }


def fetch_base_prices(card):
    try:
        return fetch_yuyutei(card["japaneseBaseName"], card["sets"]), []
    except requests.RequestException as error:
        logger.warning("Yuyu-tei fetch failed after retries: %r", error)
        return [], ["Yuyu-tei is unreachable right now — prices could not be fetched. Try again in a moment."]


def fetch_rates():
    try:
        return exchange_rate(), []
    except requests.RequestException:
        return None, ["IDR conversion unavailable"]


def add_idr_prices(listings, rate):
    rates = rate["rates"] if rate else None
    for listing in listings:
        listing["priceIdr"] = to_idr(listing["priceJpy"], "JPY", rates)


def add_ae_prices(listings, card, rate, include_ae):
    if not include_ae:
        return False, []
    if not ae_catalog_ready():
        return True, ["Asian English prices are still loading — they'll appear in a moment."]
    try:
        listings.extend(fetch_asian_english(card["canonicalName"], rate["rates"] if rate else None))
        return False, []
    except requests.RequestException as error:
        logger.warning("TCG Corner fetch failed: %r", error)
        return False, ["Asian English prices unavailable right now. Try again in a moment."]


def build_result(name, card, rate, listings, warnings, ae_pending):
    return {
        "query": name,
        "aePending": ae_pending,
        "card": card,
        "exchangeRate": rate,
        "filters": available_filters(listings),
        "listings": listings,
        "warnings": warnings,
        "yuyuteiSearchUrl": YUYUTEI_SEARCH_URL + "?" + urlencode({
            "search_word": unicodedata.normalize("NFKC", card["japaneseBaseName"]).replace("\u2010", "-")
        }),
        "tcgCornerSearchUrl": "https://tcg-corner.com/search?" + urlencode({"q": card["canonicalName"]}),
    }


def card_price(name, selected_title=None, page=0, candidates_only=False, include_ae=False):
    key = f"{name.strip().lower()}::{(selected_title or '').lower()}::ae={int(include_ae)}"
    if candidates_only or page:
        return resolve_card(name, selected_title, page, candidates_only)
    cached = cache.get(key)
    if cached is not None:
        return cached

    card = resolve_card(name, selected_title, page, candidates_only)
    if card.get("selectionRequired"):
        return card
    listings, warnings = fetch_base_prices(card)
    rate, rate_warnings = fetch_rates()
    warnings.extend(rate_warnings)
    add_idr_prices(listings, rate)
    ae_pending, ae_warnings = add_ae_prices(listings, card, rate, include_ae)
    warnings.extend(ae_warnings)
    result = build_result(name, card, rate, listings, warnings, ae_pending)
    if not ae_pending:
        cache.set(key, result, CACHE_SECONDS)
    return result
