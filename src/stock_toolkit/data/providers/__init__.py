"""Data providers interface and registry."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol

import pandas as pd

from ...models.price_series import PriceSeries


class ProviderError(RuntimeError):
    """Raised when a provider fails to retrieve data."""


class BaseProvider(Protocol):
    """Interface that all providers must implement."""

    name: str

    def fetch_price_series(
        self,
        symbol: str,
        start_date: date | None = None,
        end_date: date | None = None,
        **kwargs: object,
    ) -> PriceSeries:
        """Fetch a price series for a single symbol."""


@dataclass(slots=True)
class ProviderContext:
    """Context object shared across providers during instantiation."""

    alphavantage_api_key: str | None = None


def create_default_providers(context: ProviderContext) -> dict[str, BaseProvider]:
    """Factory for the default provider registry."""

    from .alphavantage import AlphaVantageProvider
    from .other_provider import MockProvider
    from .yahoo import YahooFinanceProvider

    providers: dict[str, BaseProvider] = {
        "yahoo": YahooFinanceProvider(),
        "alphavantage": AlphaVantageProvider(api_key=context.alphavantage_api_key),
        "mock": MockProvider(),
    }
    return providers


def dataframe_to_price_series(
    frame: pd.DataFrame,
    symbol: str,
    frequency: str = "D",
    currency: str | None = None,
) -> PriceSeries:
    """Utility to convert a pandas DataFrame into a PriceSeries instance."""

    if frame.empty:
        msg = f"No se obtuvieron datos para {symbol}"
        raise ProviderError(msg)

    frame = frame.sort_index()  # ensure chronological order

    return PriceSeries.from_dataframe(
        symbol=symbol,
        data=frame,
        frequency=frequency,
        currency=currency,
    )


