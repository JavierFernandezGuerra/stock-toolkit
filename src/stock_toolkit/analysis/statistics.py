"""Statistical helpers for price series and portfolios."""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd

from ..models.price_series import PriceSeries


def compute_log_returns(series_list: Sequence[PriceSeries]) -> pd.DataFrame:
    frames = []
    for series in series_list:
        prices = series.prices["adj_close"].astype(float)
        log_prices = prices.apply(np.log)
        log_returns = log_prices.diff().dropna()
        frames.append(log_returns.rename(series.symbol))
    combined = pd.concat(frames, axis=1).dropna()
    return combined


def compute_simple_returns(series_list: Sequence[PriceSeries]) -> pd.DataFrame:
    frames = []
    for series in series_list:
        simple_returns = series.daily_returns
        frames.append(simple_returns.rename(series.symbol))
    combined = pd.concat(frames, axis=1).dropna()
    return combined


def compute_returns(series_list: Sequence[PriceSeries], kind: str = "log") -> pd.DataFrame:
    """Compute returns for a list of series.

    kind: "simple" for arithmetic returns, "log" for log-returns.
    """
    kind_normalized = kind.lower()
    if kind_normalized not in {"simple", "log"}:
        raise ValueError("Unsupported return kind; use 'simple' or 'log'")
    if kind_normalized == "log":
        return compute_log_returns(series_list)
    return compute_simple_returns(series_list)


def annualized_return(returns: pd.Series) -> float:
    returns_float = returns.astype(float)
    compounded = float(np.prod((1.0 + returns_float).to_numpy(dtype=float), dtype=float))
    periods = int(returns_float.shape[0])
    if periods == 0:
        return 0.0
    exponent = 252.0 / float(periods)
    return float(compounded ** exponent - 1.0)


def portfolio_expected_return(weights: np.ndarray, mean_returns: pd.Series) -> float:
    return float(np.dot(weights, mean_returns) * 252)


def portfolio_volatility(weights: np.ndarray, covariance: pd.DataFrame) -> float:
    variance = weights.T @ covariance.values @ weights
    return float(np.sqrt(variance * 252))


def summary_table(series_list: Sequence[PriceSeries]) -> pd.DataFrame:
    rows = []
    for series in series_list:
        stats = series.basic_stats()
        rows.append(
            {
                "symbol": series.symbol,
                "mean_price": stats["mean"],
                "std_price": stats["std"],
                "return_annualized": stats["return_annualized"],
                "volatility_annualized": stats["volatility_annualized"],
            }
        )
    return pd.DataFrame(rows).set_index("symbol")


