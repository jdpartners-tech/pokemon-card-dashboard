import requests


def get_usd_to_hkd() -> float:
    resp = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10)
    resp.raise_for_status()
    return float(resp.json()["rates"]["HKD"])
