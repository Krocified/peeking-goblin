import re
import time
import unicodedata

import requests
from bs4 import BeautifulSoup

from config import REQUEST_TIMEOUT_SECONDS, YUYUTEI_SEARCH_URL
from http_client import session


def price(text):
    match = re.search(r"[\d,]+", text or "")
    return int(match.group(0).replace(",", "")) if match else None


def stock_state(product):
    value = product.select_one(".cart_sell_zaiko")
    text = value.get_text(" ", strip=True) if value else ""
    return {"inStock": "×" not in text, "stockText": text.replace("在庫 :", "").strip()}


def fetch_yuyutei_page(japanese_name):
    last_error = None
    for attempt in range(3):
        try:
            response = session.get(
                YUYUTEI_SEARCH_URL,
                params={"search_word": japanese_name},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return response
        except requests.RequestException as error:
            last_error = error
            session.close()
            time.sleep(1 + attempt)
    if last_error:
        raise last_error
    raise requests.RequestException("Yuyu-tei request failed")


def parse_yuyutei_product(product, japanese_name, card_sets, rarity):
    number_node = product.select_one("span.d-block.border")
    price_node = product.select_one("strong")
    set_number = number_node.get_text(strip=True) if number_node else ""
    current_price = price(price_node.get_text(" ", strip=True) if price_node else "")
    if not set_number or current_price is None:
        return None

    old_price_node = product.select_one("del")
    set_info = next((item for item in card_sets if item["setNumber"] == set_number), {})
    stock = stock_state(product)
    href_node = product.select_one("a[href]")
    image_node = product.select_one(".product-img img")
    source_url = href_node.get("href") if href_node else YUYUTEI_SEARCH_URL
    if source_url.startswith("/"):
        source_url = YUYUTEI_SEARCH_URL.split("/sell/")[0] + source_url
    old_price = price(old_price_node.get_text(" ", strip=True)) if old_price_node else None
    return {
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
    }


def parse_yuyutei_group(group, japanese_name, card_sets):
    heading = group.select_one("h3")
    rarity = heading.get_text(" ", strip=True).replace("Card List", "").strip() if heading else None
    listings = []
    for product in group.select(".card-product"):
        listing = parse_yuyutei_product(product, japanese_name, card_sets, rarity)
        if listing:
            listings.append(listing)
    return listings


def fetch_yuyutei(japanese_name, card_sets):
    japanese_name = unicodedata.normalize("NFKC", japanese_name).replace("\u2010", "-")
    response = fetch_yuyutei_page(japanese_name)
    soup = BeautifulSoup(response.text, "html.parser")
    listings = []
    for group in soup.select("#card-list3.cards-list"):
        listings.extend(parse_yuyutei_group(group, japanese_name, card_sets))
    return listings
