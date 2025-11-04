"""Alpha Vantage provider implementation."""

from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import requests

from . import ProviderContext, ProviderError, dataframe_to_price_series
from ...models.price_series import PriceSeries

ALPHAVANTAGE_URL = "https://www.alphavantage.co/query"


class AlphaVantageProvider:
    """Provider that wraps the Alpha Vantage API."""

    name = "alphavantage"

    def __init__(self, api_key: str | None) -> None:
        self.api_key = api_key

    def fetch_price_series(
        self,
        symbol: str,
        start_date: date | None = None,
        end_date: date | None = None,
        **kwargs: Any,
    ) -> PriceSeries:
        if not self.api_key:
            raise ProviderError(
                "Se requiere ALPHAVANTAGE_API_KEY para usar este proveedor"
            )

        function: str = kwargs.get("function", "TIME_SERIES_DAILY_ADJUSTED")  # type: ignore[assignment]

        params = {
            "function": function,
            "symbol": symbol,
            "apikey": self.api_key,
            "datatype": "json",
            "outputsize": "full",
        }

        response = requests.get(ALPHAVANTAGE_URL, params=params, timeout=30)
        if response.status_code != 200:
            raise ProviderError(
                f"Error HTTP {response.status_code} desde Alpha Vantage"
            )

        payload = response.json()
        key = next((k for k in payload if "Time Series" in k), None)
        if not key:
            raise ProviderError(
                "Respuesta de Alpha Vantage no contiene series temporales"
            )

        time_series = payload[key]
        data = (
            pd.DataFrame.from_dict(time_series, orient="index")
            .rename(
                columns={
                    "1. open": "open",
                    "2. high": "high",
                    "3. low": "low",
                    "4. close": "close",
                    "5. adjusted close": "adj_close",
                    "6. volume": "volume",
                }
            )
            .astype(float)
        )
        data.index = pd.to_datetime(data.index)

        if start_date or end_date:
            data = data.loc[start_date:end_date]

        return dataframe_to_price_series(
            data, symbol=symbol, frequency="1d", currency="USD"
        )

    def fetch_fundamentals(self, symbol: str, **kwargs: Any) -> pd.DataFrame:
        """Fetch a snapshot of fundamentals via Alpha Vantage OVERVIEW endpoint.

        Returns a single-row DataFrame with the raw overview fields.
        """
        if not self.api_key:
            raise ProviderError(
                "Se requiere ALPHAVANTAGE_API_KEY para usar este proveedor"
            )

        params = {
            "function": "OVERVIEW",
            "symbol": symbol,
            "apikey": self.api_key,
            "datatype": "json",
        }
        response = requests.get(ALPHAVANTAGE_URL, params=params, timeout=30)
        if response.status_code != 200:
            raise ProviderError(
                f"Error HTTP {response.status_code} desde Alpha Vantage (OVERVIEW)"
            )
        payload = response.json()
        if not isinstance(payload, dict) or not payload:
            raise ProviderError("Respuesta de Alpha Vantage OVERVIEW vacía o inválida")
        frame = pd.DataFrame([payload])
        frame.insert(0, "symbol", symbol)
        return frame

    def fetch_macro_data(self, indicator: str, **kwargs: Any) -> pd.DataFrame:
        """Fetch macro time series from Alpha Vantage for a limited set of indicators.

        Supported examples: CPI, REAL_GDP. Returns DataFrame indexed by date with a 'value' column.
        """
        if not self.api_key:
            raise ProviderError(
                "Se requiere ALPHAVANTAGE_API_KEY para usar este proveedor"
            )

        # Mappear nombres familiares a nombres de la función Alpha Vantage
        indicator_map = {
            "CPI": "CPI",
            "REAL_GDP": "REAL_GDP",
        }
        fn = indicator_map.get(indicator.upper())
        if not fn:
            raise ProviderError(
                f"Indicador macro no soportado por este proveedor: {indicator}"
            )

        params = {
            "function": fn,
            "apikey": self.api_key,
            "datatype": "json",
        }
        response = requests.get(ALPHAVANTAGE_URL, params=params, timeout=30)
        if response.status_code != 200:
            raise ProviderError(
                f"Error HTTP {response.status_code} desde Alpha Vantage ({fn})"
            )
        payload = response.json()

        # Común AV macro shape: { data: [ { 'date': 'YYYY-MM-DD', 'value': '...' }, ... ] }
        data_key = "data"
        if data_key not in payload or not isinstance(payload[data_key], list):
            raise ProviderError("Respuesta macro de Alpha Vantage no contiene 'data'")
        df = pd.DataFrame(payload[data_key])
        if "date" not in df.columns or "value" not in df.columns:
            raise ProviderError(
                "Respuesta macro de Alpha Vantage carece de columnas esperadas"
            )
        df["date"] = pd.to_datetime(df["date"])  # type: ignore[assignment]
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna(subset=["value"]).sort_values("date").set_index("date")
        return df
