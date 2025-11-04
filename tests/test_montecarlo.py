from __future__ import annotations

import pandas as pd

from stock_toolkit.analysis.montecarlo import run_portfolio_monte_carlo
from stock_toolkit.models.price_series import PriceSeries


def make_series(symbol: str, offset: float) -> PriceSeries:
    index = pd.date_range("2024-01-01", periods=20, freq="B")
    data = {
        "open": offset + pd.Series(range(20)).astype(float),
        "high": offset + pd.Series(range(20)).astype(float) + 1,
        "low": offset + pd.Series(range(20)).astype(float) - 1,
        "close": offset + pd.Series(range(20)).astype(float) + 0.5,
        "adj_close": offset + pd.Series(range(20)).astype(float) + 0.2,
        "volume": 1_000,
    }
    return PriceSeries.from_dataframe(symbol, pd.DataFrame(data, index=index))


def test_montecarlo_summary_contains_quantiles():
    series = [make_series("AAA", 100), make_series("BBB", 120)]
    result = run_portfolio_monte_carlo(series, [0.5, 0.5], periods=5, simulations=10, seed=42)
    summary = result.summary()
    assert "Simulaciones" in summary
    assert "Cuantiles" in summary

