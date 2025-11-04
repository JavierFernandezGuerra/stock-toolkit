from __future__ import annotations

import pandas as pd

from stock_toolkit.models.price_series import PriceSeries


def make_frame() -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=5, freq="B")
    data = {
        "open": [100, 101, 102, 103, 104],
        "high": [101, 102, 103, 104, 105],
        "low": [99, 100, 101, 102, 103],
        "close": [100.5, 101.5, 102.5, 103.5, 104.5],
        "adj_close": [100.2, 101.2, 102.2, 103.2, 104.2],
        "volume": [1_000, 1_200, 1_100, 1_150, 1_300],
    }
    return pd.DataFrame(data, index=index)


def test_price_series_basic_stats():
    series = PriceSeries.from_dataframe("TEST", make_frame())
    stats = series.basic_stats()
    assert stats["mean"] > 0
    assert stats["volatility_annualized"] >= 0


def test_price_series_resample():
    series = PriceSeries.from_dataframe("TEST", make_frame())
    weekly = series.resample("W")
    assert len(weekly.prices) >= 1
    assert weekly.frequency == "W"

