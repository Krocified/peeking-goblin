import os

from dotenv import load_dotenv

load_dotenv()

PORT = int(os.environ.get("PORT", 8787))
CACHE_SECONDS = int(os.environ.get("CACHE_SECONDS", 300))
REQUEST_TIMEOUT_SECONDS = int(os.environ.get("REQUEST_TIMEOUT_SECONDS", 12))
YUGIPEDIA_API_URL = os.environ.get("YUGIPEDIA_API_URL", "https://yugipedia.com/api.php")
YGOPRODECK_API_URL = os.environ.get("YGOPRODECK_API_URL", "https://db.ygoprodeck.com/api/v7/cardinfo.php")
YUYUTEI_SEARCH_URL = os.environ.get("YUYUTEI_SEARCH_URL", "https://yuyu-tei.jp/sell/ygo/s/search")
TCG_CORNER_PRODUCTS_URL = os.environ.get("TCG_CORNER_PRODUCTS_URL", "https://tcg-corner.com/products.json")
AE_CATALOG_CACHE_SECONDS = int(os.environ.get("AE_CATALOG_CACHE_SECONDS", 6 * 3600))
AE_PROBE_SECONDS = int(os.environ.get("AE_PROBE_SECONDS", 3600))
DATABASE_URL = os.environ.get("DATABASE_URL")
EXCHANGE_RATE_URL = os.environ.get("EXCHANGE_RATE_URL", "https://api.frankfurter.dev/v1/latest")
CANDIDATE_PAGE_SIZE = int(os.environ.get("CANDIDATE_PAGE_SIZE", 20))
CANDIDATE_CACHE_SECONDS = int(os.environ.get("CANDIDATE_CACHE_SECONDS", 1800))
WARM_AE = os.environ.get("WARM_AE", "1") != "0"
USER_AGENT = os.environ.get("USER_AGENT", "card-price-viewer/1.0")
allowed_origins = {
    origin.strip()
    for origin in os.environ.get("FRONTEND_ORIGINS", "*").split(",")
    if origin.strip()
}
