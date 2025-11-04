"""Portfolio dataclass aggregating multiple price series."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ..analysis.montecarlo import MonteCarloResult, run_portfolio_monte_carlo
from ..analysis.reports import portfolio_report_markdown
from ..analysis.statistics import (
    compute_returns,
    portfolio_expected_return,
    portfolio_volatility,
)
from ..utils.helpers import normalize_weights
from ..visualization import plots
from .price_series import PriceSeries


@dataclass(slots=True)
class Portfolio:
    """Portfolio composed of multiple price series with weights."""

    series: list[PriceSeries]
    weights: pd.Series = field(init=False)
    name: str = "Portfolio"

    # Valida que la cartera no esté vacía y asigna pesos iguales a los activos
    def __post_init__(self) -> None:
        if not self.series:
            raise ValueError("La cartera debe contener al menos una serie")
        symbols = [series.symbol for series in self.series]
        # Enforce unique logical assets to avoid duplicate weighting by symbol
        if len(set(symbols)) != len(symbols):
            raise ValueError("La cartera contiene símbolos duplicados; cada símbolo debe ser único")
        self.weights = pd.Series(
            normalize_weights([1.0] * len(self.series)), index=symbols, dtype=float
        )

    # Alternativa explícita, clara y semántica de crear carteras con pesos normalizados
    @classmethod
    def from_equal_weights(
        cls, series: Sequence[PriceSeries], name: str = "Portfolio"
    ) -> "Portfolio":
        portfolio = cls(series=list(series), name=name)
        portfolio.weights = pd.Series(
            normalize_weights([1.0] * len(portfolio.series)),
            index=[s.symbol for s in portfolio.series],
            dtype=float,
        )
        return portfolio

    # Alternativa para poder crear una cartera con pesos personalizados
    @classmethod
    def from_weights(
        cls,
        series: Sequence[PriceSeries],
        weights: Sequence[float],
        name: str = "Portfolio",
    ) -> "Portfolio":
        # Valida la correspondencia entre número de activos y número de pesos
        if len(series) != len(weights):
            raise ValueError("El número de pesos debe igualar el número de series")
        # Crea un pd.Series con símbolos como índice y los pesos como valores.
        portfolio = cls(series=list(series), name=name)
        # Normaliza los pesos para que sumen 1
        portfolio.weights = pd.Series(
            normalize_weights(weights),
            index=[s.symbol for s in portfolio.series],
            dtype=float,
        )
        return portfolio

    # Rendimiento esperado a partid de media rendimientos históricos por activo * pesos
    def expected_return(self, return_type: str = "log") -> float:
        returns = compute_returns(self.series, kind=return_type)
        mean_returns = returns.mean()
        return portfolio_expected_return(self.weights.to_numpy(dtype=float), mean_returns)

    # Riesgo total o volatilidad de la cartera (fórmula clásica)
    def volatility(self, return_type: str = "log") -> float:
        returns = compute_returns(self.series, kind=return_type)
        covariance = returns.cov()
        return portfolio_volatility(self.weights.to_numpy(dtype=float), covariance)

    # pd.Series indexada por fecha, que representa el valor combinado del portafolio
    def historical_value(self) -> pd.Series:
        aligned = pd.concat(
            [s.prices["adj_close"].rename(s.symbol) for s in self.series], axis=1
        ).dropna()
        return aligned.mul(self.weights, axis=1).sum(axis=1)

    # Ejecuta simulaciones de Monte Carlo para proyectar la evolución futura del portafolio
    def run_monte_carlo(
        self,
        periods: int = 252,
        simulations: int = 1_000,
        drift: float | None = None,
        volatility: float | None = None,
        seed: int | None = None,
    ) -> MonteCarloResult:
        return run_portfolio_monte_carlo(
            self.series,
            self.weights.astype(float).tolist(),
            periods=periods,
            simulations=simulations,
            drift=drift,
            volatility=volatility,
            seed=seed,
        )

    # Reporte en formato Markdown: estadísticas de rendimiento, riesgo y composición
    # Incluye posibles alertas, como por ejemplo series cortas o pesos negativos
    def report(
        self,
        include_metrics: bool = True,
        include_warnings: bool = True,
        include_montecarlo: bool = False,
        alpha: float = 0.05,
        simulations: int | None = None,
        periods: int = 252,
        drift: float | None = None,
        volatility: float | None = None,
        seed: int | None = None,
    ) -> str:
        mc_result = None
        if include_montecarlo:
            mc_result = self.run_monte_carlo(
                periods=periods,
                simulations=simulations or 1000,
                drift=drift,
                volatility=volatility,
                seed=seed,
            )
        return portfolio_report_markdown(
            self.series,
            weights=self.weights,
            include_metrics=include_metrics,
            include_warnings=include_warnings,
            montecarlo=mc_result,
            alpha=alpha,
        )

    # Crea visualizaciones de las trayectorias del portafolio y sus componentes
    def plots_report(self, montecarlo: MonteCarloResult | None = None) -> None:
        if montecarlo is None:
            montecarlo = self.run_monte_carlo(simulations=500)
        plots.plot_portfolio_paths(montecarlo)
        plots.plot_component_paths(montecarlo)
        plt.show(block=True)
