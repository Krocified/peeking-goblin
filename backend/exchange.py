from config import EXCHANGE_RATE_URL
from http_client import get_json


def exchange_rate():
    result = get_json(EXCHANGE_RATE_URL, {"base": "IDR", "symbols": "JPY,USD"})
    rates = {currency: 1 / value for currency, value in result["rates"].items()}
    return {"base": "IDR", "target": "IDR", "rates": rates, "retrievedAt": result["date"]}


def to_idr(price, currency, rates):
    if price is None or not rates or currency not in rates:
        return None
    return round(price * rates[currency])
