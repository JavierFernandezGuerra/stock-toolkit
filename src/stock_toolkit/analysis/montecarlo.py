"""Monte Carlo simulation utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Sequence

import numpy as np
import pandas as pd

from .statistics import compute_log_returns
from ..models.price_series import PriceSeries


@dataclass(slots=True)
class MonteCarloResult:
    """Container for Monte Carlo simulation outputs."""

    timeline: pd.DatetimeIndex
    portfolio_paths: pd.DataFrame
    component_paths: dict[str, pd.DataFrame]
    weights: pd.Series
    metadata: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        final_values = self.portfolio_paths.iloc[-1]
        quantiles = final_values.quantile([0.05, 0.25, 0.5, 0.75, 0.95])
        mean_final = final_values.mean()
        std_final = final_values.std(ddof=1)
        lines = [
            "Resumen Monte Carlo:",
            f"  Simulaciones: {self.portfolio_paths.shape[1]}",
            f"  Periodos: {self.portfolio_paths.shape[0] - 1}",
            f"  Valor medio final: {mean_final:,.2f}",
            f"  Desviación final: {std_final:,.2f}",
            "  Cuantiles finales:",
        ]
        q_index = [float(x) for x in quantiles.index.tolist()]
        q_values = [float(x) for x in quantiles.tolist()]
        for q, value in zip(q_index, q_values):
            percent = int(q * 100)
            lines.append(f"    p{percent:02d}: {value:,.2f}")
        return "\n".join(lines)

    def to_dataframe(self) -> pd.DataFrame:
        return self.portfolio_paths.copy()

    # --- Extended analytics ---
    def final_prices(self) -> pd.Series:
        """Return the final portfolio values across simulations as a pd.Series."""
        last_row = self.portfolio_paths.iloc[-1]
        return pd.Series(last_row.values, index=last_row.index, name="final_price")

    def value_at_risk(self, alpha: float = 0.05) -> float:
        """Historical VaR based on simulated final prices (price space)."""
        finals = self.final_prices().to_numpy(dtype=float)
        q = float(np.quantile(finals, alpha))
        return q

    def expected_shortfall(self, alpha: float = 0.05) -> float:
        """Historical CVaR (Expected Shortfall) on simulated final prices."""
        finals = self.final_prices().to_numpy(dtype=float)
        q = float(np.quantile(finals, alpha))
        tail = finals[finals < q]
        if tail.size == 0:
            return q
        return float(np.mean(tail))

    def max_drawdown_distribution(self, percent: bool = True) -> pd.Series:
        """Compute max drawdown per path.

        If percent is True, return drawdowns as percentage relative to each path's max.
        """
        # portfolio_paths shape: (periods+1, simulations)
        paths = self.portfolio_paths.to_numpy(dtype=float).T  # (simulations, periods+1)
        peaks = np.maximum.accumulate(paths, axis=1)
        drawdowns = peaks - paths
        max_dds = np.max(drawdowns, axis=1)
        if percent:
            max_vals = np.maximum(peaks.max(axis=1), 1e-12)
            max_dds = (max_dds / max_vals) * 100.0
        return pd.Series(max_dds, index=self.portfolio_paths.columns, name="max_drawdown")

    def summary_extended(self, alpha: float = 0.05) -> str:
        finals = self.final_prices()
        var_q = self.value_at_risk(alpha=alpha)
        es = self.expected_shortfall(alpha=alpha)
        dd = self.max_drawdown_distribution(percent=True)
        lines = [self.summary(), "", "Métricas adicionales:"]
        lines.append(f"  VaR p{int(alpha*100)} (precio): {var_q:,.2f}")
        lines.append(f"  CVaR p{int(alpha*100)} (precio): {es:,.2f}")
        lines.append(f"  Max DD medio (%): {float(dd.mean()):.2f}")
        lines.append(f"  Max DD mediana (%): {float(dd.median()):.2f}")
        lines.append(f"  Max DD p99 (%): {float(np.percentile(dd, 99)): .2f}")
        return "\n".join(lines)


def run_portfolio_monte_carlo(
    series_list: Sequence[PriceSeries],
    weights: Sequence[float],
    periods: int = 252,
    simulations: int = 1_000,
    drift: float | None = None,
    volatility: float | None = None,
    seed: int | None = None,
) -> MonteCarloResult:
    if len(series_list) != len(weights):
        raise ValueError("Número de pesos distinto al número de series")

    weights_array = np.asarray(weights, dtype=float)
    if weights_array.sum() == 0:
        raise ValueError("Los pesos no pueden sumar cero")
    weights_array = weights_array / weights_array.sum()

    log_returns = compute_log_returns(series_list)
    mean_vector = np.nan_to_num(log_returns.mean().to_numpy(dtype=float))
    covariance = np.nan_to_num(log_returns.cov().to_numpy(dtype=float))

    # regularize covariance to avoid singular matrices with short histories
    dim = covariance.shape[0]
    covariance = covariance + np.eye(dim) * 1e-6

    if drift is not None:
        daily_drift = np.log(1 + drift) / 252
        mean_vector = np.full_like(mean_vector, daily_drift)

    if volatility is not None:
        current_daily_vol = np.sqrt(weights_array @ covariance @ weights_array)
        target_daily_vol = volatility / np.sqrt(252)
        if current_daily_vol > 0:
            scale = target_daily_vol / current_daily_vol
            covariance = covariance * scale**2

    rng = np.random.default_rng(seed)
    draws = rng.multivariate_normal(mean=mean_vector, cov=covariance, size=(simulations, periods))

    initial_prices = np.array([series.prices["adj_close"].iloc[-1] for series in series_list])
    symbols = [series.symbol for series in series_list]
    start_date = max(series.end for series in series_list)
    timeline = pd.bdate_range(start=start_date, periods=periods + 1)

    component_paths: dict[str, pd.DataFrame] = {}
    portfolio_paths_list = []

    for idx, symbol in enumerate(symbols):
        asset_draws = draws[:, :, idx]
        asset_paths = np.exp(np.cumsum(asset_draws, axis=1)) * initial_prices[idx]
        asset_paths = np.concatenate([
            np.full((simulations, 1), initial_prices[idx]),
            asset_paths,
        ], axis=1)
        component_paths[symbol] = pd.DataFrame(
            asset_paths.T,
            index=timeline,
            columns=[f"sim_{i}" for i in range(simulations)],
        )

    # compute portfolio paths as weighted sum of component paths
    portfolio_matrix = sum(
        weights_array[idx] * component_paths[symbol].values for idx, symbol in enumerate(symbols)
    )

    portfolio_paths = pd.DataFrame(
        portfolio_matrix,
        index=timeline,
        columns=[f"sim_{i}" for i in range(simulations)],
    )

    return MonteCarloResult(
        timeline=timeline,
        portfolio_paths=portfolio_paths,
        component_paths=component_paths,
        weights=pd.Series(weights_array, index=symbols),
        metadata={"seed": seed, "drift": drift, "volatility": volatility},
    )


def run_portfolio_montecarlo(*args, **kwargs) -> MonteCarloResult:
    """Alias sin guion bajo por compatibilidad."""

    return run_portfolio_monte_carlo(*args, **kwargs)

