import time

import requests

from config import REQUEST_TIMEOUT_SECONDS, USER_AGENT

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})


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
