"""Yahoo Finance provider using yfinance."""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import yfinance as yf

from . import ProviderError, dataframe_to_price_series
from ...models.price_series import PriceSeries


class YahooFinanceProvider:
    """Provider implementation backed by yfinance."""

    name = "yahoo"

    def fetch_price_series(
        self,
        symbol: str,
        start_date: date | None = None,
        end_date: date | None = None,
        **kwargs: Any,
    ) -> PriceSeries:
        interval: str = kwargs.get("interval", "1d")  # type: ignore[assignment]
        auto_adjust: bool = kwargs.get("auto_adjust", False)  # type: ignore[assignment]
        try:
            ticker = yf.Ticker(symbol)
            data: pd.DataFrame = ticker.history(
                start=start_date,
                end=end_date,
                interval=interval,
                auto_adjust=auto_adjust,
            )
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(
                f"Error al obtener datos desde Yahoo Finance: {exc}"
            ) from exc

        data = data.rename(
            columns={
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )

        if "Adj Close" in data.columns:
            data = data.rename(columns={"Adj Close": "adj_close"})
        else:
            # Auto_adjust=True elimina adj close; en ese caso usamos close
            data["adj_close"] = data["close"]

        # Descartar columnas extra que no necesitamos
        extras = set(data.columns) - {
            "open",
            "high",
            "low",
            "close",
            "adj_close",
            "volume",
        }
        if extras:
            data = data.drop(columns=list(extras))

        return dataframe_to_price_series(
            data, symbol=symbol, frequency=interval, currency="USD"
        )

    def fetch_fundamentals(self, symbol: str, **kwargs: Any) -> pd.DataFrame:
        """Fetch a fundamentals snapshot using yfinance.

        Returns a single-row DataFrame with raw Yahoo fields.
        """
        try:
            ticker = yf.Ticker(symbol)
            # Nueva API preferible, si no usar legacy .info
            if hasattr(ticker, "get_info"):
                info = ticker.get_info()
            else:
                info = ticker.info  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(
                f"Error al obtener fundamentals desde Yahoo Finance: {exc}"
            ) from exc

        if not isinstance(info, dict) or not info:
            raise ProviderError(
                "Respuesta de Yahoo Finance sin información de fundamentals"
            )

        frame = pd.DataFrame([info])
        frame.insert(0, "symbol", symbol)
        return frame

    def fetch_macro_data(self, indicator: str, **kwargs: Any) -> pd.DataFrame:
        """Yahoo provider does not expose generic macro indicators via yfinance.

        Not supported; raise a clear error.
        """
        raise ProviderError(
            "Yahoo Finance no soporta fetch_macro_data en este proveedor"
        )
