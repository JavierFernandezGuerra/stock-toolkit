"""Mock provider for demonstration purposes."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd

from . import dataframe_to_price_series
from ...models.price_series import PriceSeries


class MockProvider:
    """Provider that generates synthetic geometric Brownian motion data."""

    name = "mock"

    def fetch_price_series(
        self,
        symbol: str,
        start_date: date | None = None,
        end_date: date | None = None,
        **kwargs: Any,
    ) -> PriceSeries:
        periods: int = int(kwargs.get("periods", 252))
        seed: int | None = kwargs.get("seed", 42)
        drift: float = float(kwargs.get("drift", 0.08))
        volatility: float = float(kwargs.get("volatility", 0.2))
        initial_price: float = float(kwargs.get("initial_price", 100.0))

        rng = np.random.default_rng(seed)
        if not start_date:
            start_date = date.today().replace(year=date.today().year - 1)

        if not end_date:
            end_date = date.today()

        index = pd.date_range(start=start_date, end=end_date, periods=periods)
        dt = 1 / 252
        random_component = rng.normal(loc=0.0, scale=np.sqrt(dt), size=periods)
        cumulative = np.cumsum(
            (drift - 0.5 * volatility**2) * dt + volatility * random_component
        )
        prices = initial_price * np.exp(cumulative)

        data = pd.DataFrame(
            {
                "open": prices,
                "high": prices * (1 + rng.normal(0.002, 0.001, size=periods)),
                "low": prices * (1 - rng.normal(0.002, 0.001, size=periods)),
                "close": prices,
                "adj_close": prices,
                "volume": rng.integers(1_000_000, 5_000_000, size=periods),
            },
            index=index,
        )

        return dataframe_to_price_series(data, symbol=symbol, frequency="1d")

    def fetch_fundamentals(self, symbol: str, **kwargs: Any) -> pd.DataFrame:
        """Return a simple synthetic fundamentals snapshot for testing."""
        now = pd.Timestamp.utcnow().normalize()
        frame = pd.DataFrame(
            {
                "symbol": [symbol],
                "date": [now],
                "revenue": [1_000_000.0],
                "ebit": [150_000.0],
                "net_income": [100_000.0],
                "shares_out": [10_000_000.0],
                "book_value": [500_000.0],
            }
        )
        return frame

    def fetch_macro_data(
        self, indicator: str, periods: int = 60, **kwargs: Any
    ) -> pd.DataFrame:
        """Return a synthetic macro time series for testing (e.g., CPI-like)."""
        end = pd.Timestamp.utcnow().normalize()
        idx = pd.date_range(end=end, periods=periods, freq="MS")
        # patrón estacional simple con ruido
        values = (
            100
            + 2 * np.sin(np.linspace(0, 6.28, periods))
            + np.random.default_rng(0).normal(0, 0.2, periods)
        )
        frame = pd.DataFrame({"value": values}, index=idx)
        return frame
