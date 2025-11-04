"""Price series dataclass."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any, Callable

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = {"open", "high", "low", "close", "adj_close", "volume"}


@dataclass(slots=True)
class PriceSeries:
    """Container for standardized price series with automatic statistics."""

    symbol: str
    prices: pd.DataFrame
    frequency: str = "1d"
    currency: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    mean_price: float = field(init=False)
    std_price: float = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.prices.index, pd.DatetimeIndex):
            raise TypeError("El índice debe ser DatetimeIndex")

        missing = REQUIRED_COLUMNS - set(self.prices.columns)
        if missing:
            raise ValueError(f"Faltan columnas requeridas: {missing}")

        self.prices = self.prices.sort_index()
        self.mean_price = float(self.prices["adj_close"].mean())
        self.std_price = float(self.prices["adj_close"].std(ddof=1))

    # Devuelven las fechas de inicio y fin de la serie temporal
    @property
    def start(self) -> datetime:
        return self.prices.index[0].to_pydatetime()

    @property
    def end(self) -> datetime:
        return self.prices.index[-1].to_pydatetime()

    # Calcula el rendimiento porcentual diario, anual compuesto y vol compuesta
    @property
    def daily_returns(self) -> pd.Series:
        return self.prices["adj_close"].pct_change().dropna()

    def annualized_return(self) -> float:
        returns = self.daily_returns
        if returns.empty:
            return 0.0
        returns_float = returns.astype(float)
        compounded = float(np.prod((1.0 + returns_float).to_numpy(dtype=float), dtype=float))
        periods = int(returns_float.shape[0])
        exponent = 252.0 / float(periods)
        return float(compounded ** exponent - 1.0)

    def annualized_volatility(self) -> float:
        returns = self.daily_returns
        return float(returns.std(ddof=1) * np.sqrt(252))

    # Devuelve un diccionario resumen con las métricas principales
    def basic_stats(self) -> dict[str, float]:
        return {
            "mean": self.mean_price,
            "std": self.std_price,
            "return_annualized": self.annualized_return(),
            "volatility_annualized": self.annualized_volatility(),
        }

    # Devuelve una copia del DataFrame original.
    def to_dataframe(self) -> pd.DataFrame:
        return self.prices.copy()

    # Re-muestreo (por ejemplo, de diario a semanal)
    def resample(self, rule: str) -> "PriceSeries":
        frame = self.prices.resample(rule).agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "adj_close": "last",
                "volume": "sum",
            }
        )
        frame = frame.dropna(how="all")
        return replace(self, prices=frame, frequency=rule)

    def apply(self, func: Callable[[pd.DataFrame], pd.DataFrame]) -> "PriceSeries":
        return replace(self, prices=func(self.prices))

    # Constructor alternativo que facilita crear la clase desde un DataFrame
    @classmethod
    def from_dataframe(
        cls,
        symbol: str,
        data: pd.DataFrame,
        frequency: str = "1d",
        currency: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "PriceSeries":
        # Convierte el índice a DatetimeIndex si no lo es
        frame = data.copy()
        if not isinstance(frame.index, pd.DatetimeIndex):
            frame.index = pd.to_datetime(frame.index)
        # Valida las columnas
        missing = REQUIRED_COLUMNS - set(frame.columns)
        if missing:
            raise ValueError(f"Faltan columnas requeridas en {symbol}: {missing}")
        # Crea la instancia garantizando el orden de columnas y metadatos
        metadata = metadata or {}
        return cls(
            symbol=symbol,
            prices=frame[sorted(REQUIRED_COLUMNS)],
            frequency=frequency,
            currency=currency,
            metadata=metadata,
        )
