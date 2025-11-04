"""Markdown report builders."""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd

from ..models.price_series import PriceSeries
from .montecarlo import MonteCarloResult
from .statistics import summary_table


def portfolio_report_markdown(
    series_list: Sequence[PriceSeries],
    weights: pd.Series,
    include_metrics: bool = True,
    include_warnings: bool = True,
    montecarlo: MonteCarloResult | None = None,
    alpha: float = 0.05,
) -> str:
    lines = ["# Portfolio Report", "", "## Composición"]

    weight_table = pd.DataFrame({"weight": weights}).T
    lines.append(weight_table.to_markdown())

    if include_metrics:
        lines.append("\n## Métricas por activo")
        metrics = summary_table(series_list)
        lines.append(metrics.to_markdown())

    if include_warnings:
        warnings = []
        for series in series_list:
            if len(series.daily_returns) < 30:
                warnings.append(f"- Serie {series.symbol} con histórico reducido")
        if warnings:
            lines.append("\n## Advertencias")
            lines.extend(warnings)

    if montecarlo is not None:
        lines.append("\n## Simulación Monte Carlo")
        finals = montecarlo.final_prices()
        p5 = float(np.percentile(finals, 5))
        p50 = float(np.percentile(finals, 50))
        p95 = float(np.percentile(finals, 95))
        var_q = float(montecarlo.value_at_risk(alpha=alpha))
        es = float(montecarlo.expected_shortfall(alpha=alpha))
        dd = montecarlo.max_drawdown_distribution(percent=True)
        lines.extend(
            [
                f"- Percentiles finales: p5={p5:,.2f}, p50={p50:,.2f}, p95={p95:,.2f}",
                f"- VaR (α={alpha:.2f}) precio: {var_q:,.2f}",
                f"- CVaR (α={alpha:.2f}) precio: {es:,.2f}",
                f"- Max drawdown medio (%): {float(dd.mean()):.2f} | mediana: {float(dd.median()):.2f} | p99: {float(np.percentile(dd, 99)):.2f}",
            ]
        )

    return "\n".join(lines)
