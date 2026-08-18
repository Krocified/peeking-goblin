import logging
import re
import threading
import time
from difflib import SequenceMatcher

import requests
from psycopg2 import Error as DatabaseError

from config import AE_CATALOG_CACHE_SECONDS, AE_PROBE_SECONDS, TCG_CORNER_PRODUCTS_URL
from db import load_catalog, save_catalog
from exchange import to_idr
from http_client import get_json

AE_SET_NUMBER = re.compile(r"^.+-AE.{3}$")
AE_TITLE = re.compile(
    r"^(?P<setNumber>\S++)\s++(?P<name>[^()]+)\s*+"
    r"\((?P<rarity>[^()]*+)\)(?:\s*+\((?P<condition>[^()]*+)\))?$"
)
ae_catalog_cache = {"expires": 0, "value": None, "max_published": None}
ae_catalog_lock = threading.RLock()
logger = logging.getLogger(__name__)


def ae_catalog_ready():
    return ae_catalog_cache["value"] is not None and ae_catalog_cache["expires"] > time.time()


def fetch_catalog_page(page):
    for attempt in range(4):
        try:
            body = get_json(TCG_CORNER_PRODUCTS_URL, {"limit": 250, "page": page})
            return body.get("products", [])
        except requests.RequestException as error:
            if error.response is None or error.response.status_code != 429 or attempt == 3:
                raise
            time.sleep(3 * (attempt + 1))


def parse_ae_product(product):
    match = AE_TITLE.match(product.get("title", ""))
    if not match or not AE_SET_NUMBER.match(match.group("setNumber")):
        return None
    variant = (product.get("variants") or [{}])[0]
    return {
        "name": match.group("name").strip(),
        "setNumber": match.group("setNumber"),
        "rarity": match.group("rarity") or None,
        "condition": match.group("condition") or None,
        "priceUsd": float(variant.get("price") or 0),
        "inStock": bool(variant.get("available")),
        "imageUrl": (product.get("images") or [{}])[0].get("src"),
        "sourceUrl": f"https://tcg-corner.com/products/{product.get('handle', '')}",
    }


def fetch_full_catalog():
    catalog = []
    max_published = ""
    page = 1
    products = fetch_catalog_page(page)
    while products:
        for product in products:
            max_published = max(max_published, product.get("published_at") or "")
            item = parse_ae_product(product)
            if item:
                catalog.append(item)
        page += 1
        time.sleep(1.0)
        products = fetch_catalog_page(page)
    return catalog, max_published


def refresh_catalog():
    catalog, max_published = fetch_full_catalog()
    with ae_catalog_lock:
        ae_catalog_cache["value"] = catalog
        ae_catalog_cache["max_published"] = max_published
        ae_catalog_cache["expires"] = time.time() + AE_CATALOG_CACHE_SECONDS
    try:
        save_catalog(catalog, max_published)
    except DatabaseError as error:
        logger.warning("AE catalog DB save failed: %r", error)
    return catalog


def ae_catalog():
    if ae_catalog_ready():
        return ae_catalog_cache["value"]
    with ae_catalog_lock:
        if ae_catalog_ready():
            return ae_catalog_cache["value"]
        try:
            row = load_catalog()
        except DatabaseError as error:
            logger.warning("AE catalog DB load failed: %r", error)
            row = None
        if row:
            catalog, max_published, fetched_at = row
            ae_catalog_cache["value"] = catalog
            ae_catalog_cache["max_published"] = max_published
            ae_catalog_cache["expires"] = fetched_at + AE_CATALOG_CACHE_SECONDS
            if not ae_catalog_ready():
                threading.Thread(target=refresh_catalog, daemon=True).start()
            return catalog
        return refresh_catalog()


def fetch_asian_english(canonical_name, rates):
    listings = []
    lowered = canonical_name.strip().lower()
    for item in ae_catalog():
        if lowered != item["name"].strip().lower() and SequenceMatcher(
            None, lowered, item["name"].strip().lower()
        ).ratio() < 0.85:
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


def maintain_loop():
    try:
        ae_catalog()
    except (DatabaseError, requests.RequestException) as error:
        logger.warning("AE catalog warm failed: %r", error)
    while True:
        if not ae_catalog_ready() or time.time() >= ae_catalog_cache["expires"]:
            try:
                refresh_catalog()
            except requests.RequestException as error:
                logger.warning("AE catalog refresh failed: %r", error)
            time.sleep(60)
            continue
        time.sleep(AE_PROBE_SECONDS)
        try:
            body = get_json(TCG_CORNER_PRODUCTS_URL, {"limit": 250, "page": 1})
            newest = max((product.get("published_at") or "") for product in body.get("products", []))
            if newest and newest != ae_catalog_cache["max_published"]:
                logger.info(
                    "TCG Corner catalog changed (%s -> %s); refreshing",
                    ae_catalog_cache["max_published"],
                    newest,
                )
                refresh_catalog()
        except requests.RequestException as error:
            logger.warning("AE catalog probe failed: %r", error)
