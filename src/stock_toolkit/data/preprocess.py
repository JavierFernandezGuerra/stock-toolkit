"""Preprocessing utilities for price series."""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable, Sequence

import pandas as pd

from ..models.price_series import PriceSeries, REQUIRED_COLUMNS


def validate_price_series(series: PriceSeries) -> PriceSeries:
    """Strictly validate a price series without applying silent fixes.

    - DatetimeIndex, monotonic increasing, unique
    - Required columns present and numeric
    - Prices non-negative
    - No entirely empty rows
    """

    frame = series.to_dataframe()

    # Index checks
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise TypeError(f"{series.symbol}: El índice debe ser DatetimeIndex")
    if not frame.index.is_monotonic_increasing:
        raise ValueError(f"{series.symbol}: El índice temporal debe ser creciente")
    if frame.index.has_duplicates:
        raise ValueError(f"{series.symbol}: El índice temporal contiene duplicados")

    # Structure checks
    missing = REQUIRED_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"{series.symbol}: Faltan columnas requeridas: {missing}")

    # Type/values checks
    numeric_cols = list(REQUIRED_COLUMNS)
    if not all(pd.api.types.is_numeric_dtype(frame[c]) for c in numeric_cols):
        raise TypeError(f"{series.symbol}: Todas las columnas deben ser numéricas")
    if (frame[["open", "high", "low", "close", "adj_close"]] < 0).any().any():
        raise ValueError(f"{series.symbol}: Los precios no pueden ser negativos")

    # Drop fully empty rows but error if becomes empty
    frame = frame.dropna(how="all")
    if frame.empty:
        raise ValueError(f"La serie {series.symbol} quedó vacía tras la validación")

    return replace(series, prices=frame)


def align_series(series_list: Sequence[PriceSeries], method: str = "inner") -> list[PriceSeries]:
    """Align multiple series on the same date index."""

    if not series_list:
        return []

    index = None
    if method == "inner":
        index = series_list[0].prices.index
        for series in series_list[1:]:
            index = index.intersection(series.prices.index)
    elif method == "outer":
        index = series_list[0].prices.index
        for series in series_list[1:]:
            index = index.union(series.prices.index)
    else:
        raise ValueError("Método de alineación no soportado")

    aligned: list[PriceSeries] = []
    for series in series_list:
        frame = series.prices.reindex(index)
        aligned.append(replace(series, prices=frame))
    return aligned


def fill_missing(series: PriceSeries, method: str = "ffill") -> PriceSeries:
    frame = series.prices.copy()
    if method == "ffill":
        frame = frame.ffill()
    elif method == "bfill":
        frame = frame.bfill()
    elif method == "interpolate":
        frame = frame.interpolate()
    else:
        raise ValueError("Método de imputación no soportado")
    return replace(series, prices=frame)


def resample_series(series: PriceSeries, rule: str = "1D") -> PriceSeries:
    frame = series.prices.resample(rule).agg(
        {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "adj_close": "last",
            "volume": "sum",
        }
    )
    return replace(series, prices=frame.dropna(how="all"))


