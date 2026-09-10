from datetime import date

import httpx
import pytest

from data.models import HistoricalQuery
from data.upstox import UpstoxApiError, UpstoxCandleProvider


def test_upstox_provider_maps_historical_candles() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-token"
        assert request.url.path.endswith("/day/2024-01-02/2024-01-01")
        return httpx.Response(
            200,
            json={
                "status": "success",
                "data": {
                    "candles": [
                        ["2024-01-02T00:00:00+05:30", 100, 110, 95, 105, 1000, 0]
                    ]
                },
            },
        )

    provider = UpstoxCandleProvider(
        access_token="test-token", transport=httpx.MockTransport(handler)
    )
    query = HistoricalQuery("NSE_EQ|ONE", date(2024, 1, 1), date(2024, 1, 2))

    candles = provider.fetch_candles(query)

    assert candles[0].close == 105.0
    assert candles[0].timestamp.isoformat() == "2024-01-01T18:30:00+00:00"


def test_upstox_provider_passes_intraday_interval() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/5minute/2024-01-02/2024-01-01")
        return httpx.Response(200, json={"data": {"candles": []}})

    provider = UpstoxCandleProvider(
        access_token="test-token", transport=httpx.MockTransport(handler)
    )
    query = HistoricalQuery(
        "NSE_EQ|ONE",
        date(2024, 1, 1),
        date(2024, 1, 2),
        interval="5minute",
    )

    assert provider.fetch_candles(query) == []


def test_upstox_provider_raises_typed_error() -> None:
    provider = UpstoxCandleProvider(
        access_token="test-token",
        transport=httpx.MockTransport(lambda request: httpx.Response(401)),
    )
    query = HistoricalQuery("NSE_EQ|ONE", date(2024, 1, 1), date(2024, 1, 2))

    with pytest.raises(UpstoxApiError, match="401"):
        provider.fetch_candles(query)
