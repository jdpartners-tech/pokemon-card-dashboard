import pytest
import requests
from unittest.mock import patch, MagicMock
from backend.scrapers.fx import get_usd_to_hkd


def test_get_usd_to_hkd_returns_float():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"rates": {"HKD": 7.85}, "result": "success"}
    mock_resp.raise_for_status.return_value = None
    with patch("backend.scrapers.fx.requests.get", return_value=mock_resp):
        rate = get_usd_to_hkd()
    assert isinstance(rate, float)
    assert rate == 7.85


def test_get_usd_to_hkd_raises_on_http_error():
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
    with patch("backend.scrapers.fx.requests.get", return_value=mock_resp):
        with pytest.raises(requests.exceptions.HTTPError):
            get_usd_to_hkd()
