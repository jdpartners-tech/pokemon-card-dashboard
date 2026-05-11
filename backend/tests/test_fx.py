import pytest
import requests
from backend.scrapers.fx import get_usd_to_hkd


def test_get_usd_to_hkd_returns_float(requests_mock):
    requests_mock.get(
        "https://open.er-api.com/v6/latest/USD",
        json={"rates": {"HKD": 7.85}, "result": "success"},
    )
    rate = get_usd_to_hkd()
    assert isinstance(rate, float)
    assert rate == 7.85


def test_get_usd_to_hkd_raises_on_http_error(requests_mock):
    requests_mock.get("https://open.er-api.com/v6/latest/USD", status_code=500)
    with pytest.raises(requests.exceptions.HTTPError):
        get_usd_to_hkd()
