import re
from difflib import SequenceMatcher
from urllib.parse import quote

import requests

from cache import TTLCache
from config import (
    CANDIDATE_CACHE_SECONDS,
    CANDIDATE_PAGE_SIZE,
    YGOPRODECK_API_URL,
    YUGIPEDIA_API_URL,
)
from http_client import get_json
from wikitext import (
    card_image_filename,
    clean_wikitext,
    field,
    is_physical_card,
    parse_card_image,
    parse_sets,
)

candidate_cache = TTLCache()


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
                    "id": card.get("id"),
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


def yugipedia_canonical_candidates(candidates):
    if not candidates:
        return []
    result = get_json(YUGIPEDIA_API_URL, {
        "action": "query",
        "prop": "revisions",
        "rvprop": "content",
        "redirects": 1,
        "format": "json",
        "titles": "|".join(candidate["name"] for candidate in candidates),
    })
    query = result.get("query", {})
    redirects = {item["from"]: item["to"] for item in query.get("redirects", [])}
    pages = {}
    for page in query.get("pages", {}).values():
        revision = (page.get("revisions") or [{}])[0]
        pages[page.get("title", "")] = revision.get("*", "")
    canonical = []
    for candidate in candidates:
        title = redirects.get(candidate["name"], candidate["name"])
        wikitext = pages.get(title, "")
        if not is_physical_card(title, wikitext):
            continue
        password = field(wikitext, "password").strip()
        if candidate.get("id") and password and str(candidate["id"]) != password:
            continue
        canonical.append({
            "name": title,
            "source": "yugipedia",
            "imageFilename": card_image_filename(wikitext),
        })
    return canonical


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
    if cached is not None:
        return cached

    if is_latin_query(name):
        fast_candidates = yugipedia_canonical_candidates(ygoprodeck_candidates(name))
        if fast_candidates:
            candidate_cache.set(key, fast_candidates, CANDIDATE_CACHE_SECONDS)
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
    candidate_cache.set(key, catalog, CANDIDATE_CACHE_SECONDS)
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

    page_data = get_json(YUGIPEDIA_API_URL, {
        "action": "parse",
        "page": title,
        "prop": "wikitext",
        "format": "json",
    })
    parsed = page_data.get("parse", {})
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
