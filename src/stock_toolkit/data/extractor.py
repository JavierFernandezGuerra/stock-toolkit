"""Data extraction orchestrator."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from typing import Iterable, Mapping, Sequence

from ..config import Settings, get_settings
from ..models.price_series import PriceSeries
from .providers import (
    BaseProvider,
    ProviderContext,
    ProviderError,
    create_default_providers,
)


class DataExtractor:
    """Coordinates data retrieval from multiple providers."""

    def __init__(
        self,
        providers: Mapping[str, BaseProvider],
        default_provider: str | None = None,
        max_workers: int = 4,
    ) -> None:
        # accept any Mapping to be type-friendly (dict is invariant)
        self.providers = dict(providers)
        self.default_provider = default_provider or "yahoo"
        self.max_workers = max_workers

    @classmethod
    def from_config(cls, settings: Settings | None = None) -> "DataExtractor":
        settings = settings or get_settings()
        context = ProviderContext(alphavantage_api_key=settings.alphavantage_api_key)
        providers = create_default_providers(context)
        return cls(
            providers=providers,
            default_provider=settings.default_provider,
            max_workers=settings.max_workers,
        )

    def register_provider(self, provider: BaseProvider) -> None:
        self.providers[provider.name] = provider

    def get_provider(self, name: str | None = None) -> BaseProvider:
        provider_name = name or self.default_provider
        if provider_name not in self.providers:
            msg = f"Proveedor '{provider_name}' no soportado. Soportados: {sorted(self.providers)}"
            raise ProviderError(msg)
        return self.providers[provider_name]

    def fetch_one(
        self,
        symbol: str,
        provider: str | None = None,
        start_date: date | str | None = None,
        end_date: date | str | None = None,
        **kwargs: object,
    ) -> PriceSeries:
        provider_instance = self.get_provider(provider)
        # coerce ISO strings to date
        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date).date()
        if isinstance(end_date, str):
            end_date = datetime.fromisoformat(end_date).date()
        return provider_instance.fetch_price_series(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            **kwargs,
        )

    def fetch_many(
        self,
        symbols: Sequence[str] | Iterable[str],
        provider: str | None = None,
        start_date: date | str | None = None,
        end_date: date | str | None = None,
        **kwargs: object,
    ) -> list[PriceSeries]:
        """Fetch multiple series concurrently."""

        provider_instance = self.get_provider(provider)
        # coerce ISO strings to date
        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date).date()
        if isinstance(end_date, str):
            end_date = datetime.fromisoformat(end_date).date()
        results: list[PriceSeries] = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_symbol = {
                executor.submit(
                    provider_instance.fetch_price_series,
                    symbol,
                    start_date,
                    end_date,
                    **kwargs,
                ): symbol
                for symbol in symbols
            }

            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    series = future.result()
                except Exception as exc:  # noqa: BLE001
                    raise ProviderError(f"Error al obtener {symbol}: {exc}") from exc
                results.append(series)

        results.sort(key=lambda s: s.symbol)
        return results

    def fetch_fundamentals(
        self, symbol: str, provider: str | None = None, **kwargs: object
    ):
        """Fetch fundamentals for a symbol if the provider supports it.

        Returns provider-defined structure (e.g., DataFrame or dict).
        """
        provider_instance = self.get_provider(provider)
        if hasattr(provider_instance, "fetch_fundamentals"):
            return getattr(provider_instance, "fetch_fundamentals")(
                symbol=symbol, **kwargs
            )
        msg = f"El proveedor '{provider_instance.name}' no soporta fetch_fundamentals"
        raise ProviderError(msg)

    def fetch_macro_data(
        self, indicator: str, provider: str | None = None, **kwargs: object
    ):
        """Fetch macroeconomic time series if the provider supports it.

        Returns provider-defined structure (e.g., DataFrame or dict).
        """
        provider_instance = self.get_provider(provider)
        if hasattr(provider_instance, "fetch_macro_data"):
            return getattr(provider_instance, "fetch_macro_data")(
                indicator=indicator, **kwargs
            )
        msg = f"El proveedor '{provider_instance.name}' no soporta fetch_macro_data"
        raise ProviderError(msg)
