"""Visualization helpers using matplotlib."""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import numpy as np

from ..analysis.montecarlo import MonteCarloResult


def plot_portfolio_paths(result: MonteCarloResult) -> Figure:
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(result.portfolio_paths.index, result.portfolio_paths.values, color="tab:blue", alpha=0.1)

    final_values = result.portfolio_paths.iloc[-1]
    quantiles = np.percentile(final_values, [5, 50, 95])
    ax.axhline(quantiles[1], color="black", linestyle="--", label="Mediana final")
    ax.axhline(quantiles[0], color="red", linestyle=":", label="p5")
    ax.axhline(quantiles[2], color="green", linestyle=":", label="p95")

    ax.set_title("Simulación Monte Carlo - Cartera")
    ax.set_xlabel("Fecha")
    ax.set_ylabel("Valor")
    ax.legend()
    ax.grid(True, linestyle=":", alpha=0.3)
    fig.tight_layout()
    return fig


def plot_component_paths(result: MonteCarloResult) -> Figure:
    fig, ax = plt.subplots(figsize=(10, 6))
    for symbol, frame in result.component_paths.items():
        ax.plot(frame.index, frame.mean(axis=1), label=f"{symbol} media")
    ax.set_title("Componentes promedio")
    ax.set_xlabel("Fecha")
    ax.set_ylabel("Precio")
    ax.legend()
    ax.grid(True, linestyle=":", alpha=0.3)
    fig.tight_layout()
    return fig


def plot_final_distribution(result: MonteCarloResult, alpha: float = 0.05, show_fit: bool = False) -> Figure:
    finals = result.final_prices().to_numpy(dtype=float)
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.hist(finals, bins=50, density=True, orientation="horizontal", color="deepskyblue", edgecolor="navy", alpha=0.7)

    mu = float(np.mean(finals))
    sigma = float(np.std(finals))
    var_q = float(np.quantile(finals, alpha))
    cvar_mask = finals < var_q
    cvar = float(mu) if not cvar_mask.any() else float(np.mean(finals[cvar_mask]))

    if show_fit and sigma > 0:
        from scipy.stats import norm  # optional dependency; requires scipy
        x = np.linspace(finals.min(), finals.max(), 500)
        p = norm.pdf(x, loc=mu, scale=sigma)
        ax.plot(p, x, linewidth=2.0, color="orange", label="Ajuste normal")

    ax.axhline(mu, color="navy", linestyle="--", linewidth=2, label=f"Media: {mu:,.2f}")
    ax.axhline(var_q, color="purple", linestyle="--", linewidth=2, label=f"VaR α={alpha:.2f}: {var_q:,.2f}")
    ax.axhline(cvar, color="green", linestyle="--", linewidth=2, label=f"CVaR α={alpha:.2f}: {cvar:,.2f}")

    ax.set_title("Distribución de precios finales (VaR/CVaR)")
    ax.set_xlabel("Densidad")
    ax.set_ylabel("Precio final")
    ax.legend()
    ax.grid(True, linestyle=":", alpha=0.3)
    fig.tight_layout()
    return fig


def plot_drawdown_distribution(result: MonteCarloResult, percent: bool = True) -> Figure:
    dd = result.max_drawdown_distribution(percent=percent).to_numpy(dtype=float)
    fig, ax = plt.subplots(figsize=(8, 5))
    counts, bins, _ = ax.hist(dd, bins=50, color="coral", edgecolor="black", alpha=0.7)

    mean_dd = float(np.mean(dd))
    median_dd = float(np.median(dd))
    p99_dd = float(np.percentile(dd, 99))
    max_dd = float(np.max(dd))

    ax.axvline(mean_dd, color="blue", linestyle="--", linewidth=2, label=f"Media = {mean_dd:.2f}{'%' if percent else ''}")
    ax.axvline(median_dd, color="green", linestyle="-.", linewidth=2, label=f"Mediana = {median_dd:.2f}{'%' if percent else ''}")
    ax.axvline(p99_dd, color="purple", linestyle=":", linewidth=2, label=f"p99 = {p99_dd:.2f}{'%' if percent else ''}")

    # annotate max
    bin_idx = np.digitize(max_dd, bins) - 1
    bin_height = counts[bin_idx] if 0 <= bin_idx < len(counts) else 0
    ax.text(max_dd, bin_height + 1, f"Max: {max_dd:.2f}{'%' if percent else ''}", ha="center", va="bottom", fontsize=10, color="grey")

    ax.set_title("Distribución de Max Drawdowns por trayectoria")
    ax.set_xlabel(f"Max Drawdown{' (%)' if percent else ''}")
    ax.set_ylabel("Frecuencia")
    ax.legend()
    ax.grid(True, linestyle=":", alpha=0.3)
    fig.tight_layout()
    return fig


def plot_fan_chart(result: MonteCarloResult, quantiles: tuple[int, int, int, int, int] = (5, 25, 50, 75, 95), max_paths: int = 0) -> Figure:
    # Optionally plot a subset of paths faintly in background
    fig, ax = plt.subplots(figsize=(10, 6))
    if max_paths and max_paths > 0:
        sample = result.portfolio_paths.iloc[:, : min(max_paths, result.portfolio_paths.shape[1])]
        ax.plot(sample.index, sample.values, color="tab:blue", alpha=0.05, linewidth=0.8)

    # Percentile bands
    qs = np.array(quantiles, dtype=int)
    lower1, lower2, median, upper2, upper1 = np.percentile(result.portfolio_paths.values, qs, axis=1)
    idx = result.portfolio_paths.index
    ax.fill_between(idx, lower1, upper1, color="tab:blue", alpha=0.15, label=f"p{qs[0]}–p{qs[-1]}")
    ax.fill_between(idx, lower2, upper2, color="tab:blue", alpha=0.3, label=f"p{qs[1]}–p{qs[3]}")
    ax.plot(idx, median, color="tab:blue", linewidth=2.0, label=f"p{qs[2]}")

    ax.set_title("Fan chart de percentiles (cartera)")
    ax.set_xlabel("Fecha")
    ax.set_ylabel("Valor")
    ax.legend()
    ax.grid(True, linestyle=":", alpha=0.3)
    fig.tight_layout()
    return fig


def plot_montecarlo_panel(result: MonteCarloResult, alpha: float = 0.05, max_paths: int = 1000, show_fit: bool = False) -> Figure:
    # Panel 1x2: trayectorias + hist final con VaR/CVaR
    fig = plt.figure(figsize=(14, 6))
    gs = fig.add_gridspec(1, 2, width_ratios=[4, 1])
    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[0, 1])

    # Trajectories
    n = min(max_paths, result.portfolio_paths.shape[1])
    ax0.plot(result.portfolio_paths.index, result.portfolio_paths.iloc[:, :n].values, linewidth=0.6, alpha=0.6)
    avg_traj = np.mean(result.portfolio_paths.values[:, :n], axis=1)
    ax0.plot(result.portfolio_paths.index, avg_traj, color="red", linewidth=2.0, label="Trayectoria promedio")
    start_val = float(result.portfolio_paths.iloc[0, 0])
    ax0.axhline(start_val, color="black", linestyle="--", linewidth=1.5, label=f"Valor inicial: {start_val:,.2f}")
    ax0.set_title(f"Trayectorias Monte Carlo (simulaciones: {result.portfolio_paths.shape[1]})")
    ax0.set_xlabel("Fecha")
    ax0.set_ylabel("Valor")
    ax0.legend()
    ax0.grid(True, alpha=0.2)

    # Final distribution with VaR/CVaR
    finals = result.final_prices().to_numpy(dtype=float)
    ax1.hist(finals, bins=50, density=True, orientation="horizontal", color="deepskyblue", edgecolor="navy", alpha=0.7)
    mu = float(np.mean(finals))
    sigma = float(np.std(finals))
    var_q = float(np.quantile(finals, alpha))
    cvar_mask = finals < var_q
    cvar = float(mu) if not cvar_mask.any() else float(np.mean(finals[cvar_mask]))
    if show_fit and sigma > 0:
        from scipy.stats import norm  # optional dependency; requires scipy
        x = np.linspace(finals.min(), finals.max(), 500)
        p = norm.pdf(x, loc=mu, scale=sigma)
        ax1.plot(p, x, linewidth=2.0, color="orange", label="Ajuste normal")
    ax1.axhline(mu, color="navy", linestyle="--", linewidth=2, label=f"Media: {mu:,.2f}")
    ax1.axhline(var_q, color="purple", linestyle="--", linewidth=2, label=f"VaR α={alpha:.2f}: {var_q:,.2f}")
    ax1.axhline(cvar, color="green", linestyle="--", linewidth=2, label=f"CVaR α={alpha:.2f}: {cvar:,.2f}")
    ax1.set_title("Distribución final con VaR/CVaR")
    ax1.set_xlabel("Densidad")
    ax1.set_ylabel("Precio final")
    ax1.legend()
    ax1.grid(True, linestyle=":", alpha=0.3)

    fig.tight_layout()
    return fig
