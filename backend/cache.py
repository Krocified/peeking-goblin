import threading
import time


class TTLCache:
    def __init__(self):
        self._values = {}
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            item = self._values.get(key)
            if not item or item["expires"] <= time.time():
                return None
            return item["value"]

    def set(self, key, value, ttl):
        with self._lock:
            self._values[key] = {"expires": time.time() + ttl, "value": value}
