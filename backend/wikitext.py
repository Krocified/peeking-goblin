import re
from urllib.parse import quote


def clean_wikitext(value):
    value = re.sub(r"\{\{Ruby\|([^|}]+)\|[^}]+\}\}", r"\1", value)
    value = re.sub(r"\{\{[^{}]+\}\}", "", value)
    value = re.sub(r"\[\[([^|\]]++)(?:\|[^\]]*+)?\]\]", r"\1", value)
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


def parse_card_image(wikitext):
    filename = card_image_filename(wikitext)
    return "https://yugipedia.com/wiki/Special:FilePath/" + quote(filename) if filename else None


def is_physical_card(title, wikitext):
    non_card_variant = re.search(r"\((master duel|anime|game|video game)\)", title, flags=re.I)
    return (
        not non_card_variant
        and "{{CardTable2" in wikitext
        and bool(field(wikitext, "jp_sets").strip())
        and not field(wikitext, "rush_sets").strip()
    )
