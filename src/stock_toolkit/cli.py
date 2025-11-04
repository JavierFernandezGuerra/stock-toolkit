"""Command-line interface for Stock Toolkit."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .config import Settings
from .data.extractor import DataExtractor
from .data.loader import DataLoader
from .models.portfolio import Portfolio
from .visualization import plots as viz_plots
import matplotlib.pyplot as plt

app = typer.Typer(help="Toolkit para descarga y análisis de series bursátiles")
console = Console()


def _comma_separated_symbols(symbols: str) -> list[str]:
    return [sym.strip() for sym in symbols.split(",") if sym.strip()]


def _parse_date(value: Optional[str], param_name: str) -> Optional[date]:
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise typer.BadParameter(
            f"El parámetro '{param_name}' debe tener formato AAAA-MM-DD"
        ) from exc


@app.command()
def fetch(
    symbols: str = typer.Option(
        ..., "--symbols", "-s", help="Lista de símbolos separada por comas"
    ),
    provider: str = typer.Option("yahoo", help="Proveedor de datos (yahoo, alphavantage, mock)"),
    start_date: Optional[str] = typer.Option(
        None, "--start", "--start-date", help="Fecha de inicio (AAAA-MM-DD)"
    ),
    end_date: Optional[str] = typer.Option(None, "--end", "--end-date", help="Fecha de fin (AAAA-MM-DD)"),
    output: Optional[Path] = typer.Option(None, help="Ruta para guardar en parquet"),
    max_workers: Optional[int] = typer.Option(None, help="Hilos máximos para descargas concurrentes"),
) -> None:
    """Descarga series históricas y las muestra en tabla resumida."""

    settings = Settings()
    extractor = DataExtractor.from_config(settings=settings)
    if max_workers is not None:
        extractor.max_workers = max_workers
    series_list = extractor.fetch_many(
        symbols=_comma_separated_symbols(symbols),
        provider=provider,
        start_date=_parse_date(start_date, "start"),
        end_date=_parse_date(end_date, "end"),
    )

    table = Table(title="Series descargadas")
    table.add_column("Símbolo")
    table.add_column("Filas", justify="right")
    table.add_column("Inicio")
    table.add_column("Fin")
    table.add_column("Media", justify="right")
    table.add_column("Desv. Típ.", justify="right")

    for series in series_list:
        table.add_row(
            series.symbol,
            str(len(series.prices)),
            series.start.isoformat(),
            series.end.isoformat(),
            f"{series.mean_price:.2f}",
            f"{series.std_price:.2f}",
        )

    console.print(table)

    if output:
        loader = DataLoader(base_dir=settings.data_dir)
        loader.save_price_series(series_list, output)
        console.print(f"Datos guardados en {output}")


@app.command()
def report(
    symbols: str = typer.Option(..., "--symbols", "-s", help="Símbolos separados por comas"),
    provider: str = typer.Option("yahoo", help="Proveedor de datos"),
    start_date: Optional[str] = typer.Option(None, "--start", "--start-date", help="Fecha de inicio"),
    end_date: Optional[str] = typer.Option(None, "--end", "--end-date", help="Fecha de fin"),
    weights: Optional[str] = typer.Option(None, help="Pesos separados por comas"),
    markdown_output: Optional[Path] = typer.Option(None, help="Fichero donde guardar el reporte"),
    max_workers: Optional[int] = typer.Option(None, help="Hilos máximos para descargas concurrentes"),
) -> None:
    """Genera un reporte en Markdown para una cartera igual ponderada o personalizada."""

    extractor = DataExtractor.from_config()
    if max_workers is not None:
        extractor.max_workers = max_workers
    series_list = extractor.fetch_many(
        symbols=_comma_separated_symbols(symbols),
        provider=provider,
        start_date=_parse_date(start_date, "start"),
        end_date=_parse_date(end_date, "end"),
    )

    if weights:
        weights_list = [float(value) for value in _comma_separated_symbols(weights)]
    else:
        weights_list = None

    portfolio = (
        Portfolio.from_weights(series_list, weights_list)
        if weights_list
        else Portfolio.from_equal_weights(series_list)
    )

    markdown = portfolio.report(include_metrics=True, include_warnings=True)
    console.print(markdown)

    if markdown_output:
        markdown_output.write_text(markdown, encoding="utf-8")
        console.print(f"Reporte guardado en {markdown_output}")


@app.command()
def montecarlo(
    symbols: str = typer.Option(..., "--symbols", "-s", help="Símbolos separados por comas"),
    provider: str = typer.Option("yahoo", help="Proveedor de datos"),
    periods: int = typer.Option(252, help="Número de periodos a simular"),
    simulations: int = typer.Option(1000, help="Número de simulaciones"),
    drift: Optional[float] = typer.Option(None, help="Retorno esperado anual"),
    volatility: Optional[float] = typer.Option(None, help="Volatilidad anual (sigma)"),
    seed: Optional[int] = typer.Option(None, help="Semilla aleatoria"),
    save_panel: Optional[Path] = typer.Option(None, help="Guardar panel Monte Carlo en imagen (PNG/SVG)"),
    show: bool = typer.Option(True, "--show/--no-show", help="Mostrar gráficos en pantalla"),
    max_workers: Optional[int] = typer.Option(None, help="Hilos máximos para descargas concurrentes"),
) -> None:
    """Ejecuta una simulación de Monte Carlo y muestra resultados resumidos."""

    extractor = DataExtractor.from_config()
    if max_workers is not None:
        extractor.max_workers = max_workers
    series_list = extractor.fetch_many(
        symbols=_comma_separated_symbols(symbols),
        provider=provider,
    )

    portfolio = Portfolio.from_equal_weights(series_list)
    simulation = portfolio.run_monte_carlo(
        periods=periods,
        simulations=simulations,
        drift=drift,
        volatility=volatility,
        seed=seed,
    )

    summary = simulation.summary()
    console.print(summary)

    # Visualización configurable
    fig = viz_plots.plot_montecarlo_panel(simulation)
    if save_panel is not None:
        save_panel.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_panel, dpi=150)
        console.print(f"Gráfico guardado en {save_panel}")
    if show:
        plt.show(block=True)


@app.command()
def fundamentals(
    symbol: str = typer.Option(..., "--symbol", "-s", help="Símbolo a consultar"),
    provider: str = typer.Option("alphavantage", help="Proveedor de datos (alphavantage, yahoo, mock)"),
    output: Optional[Path] = typer.Option(None, help="Ruta para guardar (parquet/csv)"),
) -> None:
    """Obtiene un snapshot de fundamentales y lo muestra/guarda."""

    extractor = DataExtractor.from_config()
    frame = extractor.fetch_fundamentals(symbol=symbol, provider=provider)
    console.print(frame.head())
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.suffix.lower() == ".parquet":
            frame.to_parquet(output)
        else:
            frame.to_csv(output, index=False)
        console.print(f"Fundamentales guardados en {output}")


@app.command()
def macro(
    indicator: str = typer.Option(..., "--indicator", "-i", help="Indicador macro (p.ej., CPI, REAL_GDP)"),
    provider: str = typer.Option("alphavantage", help="Proveedor de datos (alphavantage, mock)"),
    output: Optional[Path] = typer.Option(None, help="Ruta para guardar (parquet/csv)"),
) -> None:
    """Obtiene una serie macroeconómica y la muestra/guarda."""

    extractor = DataExtractor.from_config()
    frame = extractor.fetch_macro_data(indicator=indicator, provider=provider)
    console.print(frame.head())
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.suffix.lower() == ".parquet":
            frame.to_parquet(output)
        else:
            frame.to_csv(output)
        console.print(f"Indicador macro guardado en {output}")


def run() -> None:
    app()


if __name__ == "__main__":
    run()

