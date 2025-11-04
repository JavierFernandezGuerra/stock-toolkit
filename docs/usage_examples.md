# Ejemplos de uso

## Descargar datos desde la CLI

```bash
stock-toolkit fetch --provider yahoo --symbols AAPL,MSFT,EURUSD=X --start 2020-01-01 --end 2024-12-31
```

## Cargar datos en Python

```python
from stock_toolkit.data.extractor import DataExtractor
from stock_toolkit.models.portfolio import Portfolio

extractor = DataExtractor.from_config()
series = extractor.fetch_many(["AAPL", "MSFT"], provider="yahoo", start_date="2020-01-01")

portfolio = Portfolio.from_equal_weights(series)
report = portfolio.report(include_metrics=True, include_warnings=True)
print(report)
```

## Ejecutar simulación de Monte Carlo

```python
simulation = portfolio.run_monte_carlo(periods=252, simulations=5000, drift=0.08, volatility=0.2)
simulation.summary()
portfolio.plots_report(simulation)
```

## Gráficos avanzados de Monte Carlo

```python
from stock_toolkit.visualization import plots

# Panel trayectorias + distribución final con VaR/CVaR
plots.plot_montecarlo_panel(simulation, alpha=0.05, max_paths=500, show_fit=False)

# Fan chart de percentiles
plots.plot_fan_chart(simulation, quantiles=(5,25,50,75,95), max_paths=300)

# Distribución de precios finales (VaR/CVaR)
plots.plot_final_distribution(simulation, alpha=0.01)

# Distribución de max drawdowns (% por trayectoria)
plots.plot_drawdown_distribution(simulation, percent=True)
```

## Reporte con sección de Monte Carlo

```python
report_md = portfolio.report(
    include_metrics=True,
    include_warnings=True,
    include_montecarlo=True,
    alpha=0.05,
    simulations=2000,
    periods=252,
    drift=None,
    volatility=None,
    seed=123,
)
print(report_md)
```

## Extender con un nuevo proveedor

1. Implementa una clase que cumpla la interfaz `BaseProvider`.
2. Regístrala en tiempo de ejecución con `DataExtractor.register_provider(...)` o extiende la fábrica `data.providers.create_default_providers(...)`.
3. Usa la CLI o la API para descargar desde el nuevo proveedor.


