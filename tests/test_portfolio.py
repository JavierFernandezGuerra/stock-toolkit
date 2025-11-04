from __future__ import annotations

import pandas as pd

from stock_toolkit.models.portfolio import Portfolio
from stock_toolkit.models.price_series import PriceSeries


def make_series(symbol: str, start: float) -> PriceSeries:
    index = pd.date_range("2024-01-01", periods=5, freq="B")
    data = {
        "open": start + pd.Series(range(5)).astype(float),
        "high": start + pd.Series(range(5)).astype(float) + 1,
        "low": start + pd.Series(range(5)).astype(float) - 1,
        "close": start + pd.Series(range(5)).astype(float) + 0.5,
        "adj_close": start + pd.Series(range(5)).astype(float) + 0.2,
        "volume": [1_000, 1_100, 1_200, 1_150, 1_250],
    }
    frame = pd.DataFrame(data, index=index)
    return PriceSeries.from_dataframe(symbol, frame)


def test_portfolio_equal_weights():
    series = [make_series("AAA", 100), make_series("BBB", 200)]
    portfolio = Portfolio.from_equal_weights(series)
    assert portfolio.weights.sum() == 1
    assert set(portfolio.weights.index) == {"AAA", "BBB"}


def test_portfolio_montecarlo_shape():
    series = [make_series("AAA", 100), make_series("BBB", 200)]
    portfolio = Portfolio.from_equal_weights(series)
    result = portfolio.run_monte_carlo(periods=10, simulations=50, seed=123)
    assert result.portfolio_paths.shape == (11, 50)


