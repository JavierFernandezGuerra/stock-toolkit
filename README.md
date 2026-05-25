# Stock Toolkit

![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue)
![Typer CLI](https://img.shields.io/badge/CLI-Typer-orange)
![License](https://img.shields.io/badge/license-MIT-green)

Stock Toolkit is a plug-and-play set of utilities for **equity data extraction, normalisation, analysis and visualisation**. The goal is to showcase a clean, scalable architecture that makes it easy to plug in new data providers, analytical models and reproducible workflows.

## Key features

- **Multi-provider extractor**: orchestration layer that downloads historical price series for stocks, indices and other financial time series from configurable providers (Yahoo Finance, Alpha Vantage and custom providers).
- **Typed data models**: `PriceSeries` and `Portfolio` dataclasses that standardise data structure, apply basic statistics automatically and expose methods for deeper analysis.
- **Monte Carlo simulation**: forward-looking scenario generation at both single-asset and full-portfolio level, with tunable parameters.
- **Preprocessing and validation**: utilities to clean, align and enrich time series prior to analysis or storage.
- **Visualisations**: user-ready reports with key charts and Markdown summaries.
- **Typer-based CLI**: command-line interface for running typical workflows without touching code.

## Project structure

```text
miax-stock-toolkit/
├── README.md
├── LICENSE
├── pyproject.toml
├── requirements.txt
├── docs/
│   ├── architecture_diagram.png
│   └── usage_examples.md
├── data/
│   ├── raw/
│   ├── processed/
│   └── reports/
├── notebooks/
│   ├── exploratory_analysis.ipynb
│   └── montecarlo_demo.ipynb
├── src/
│   └── stock_toolkit/
│       ├── __init__.py
│       ├── cli.py
│       ├── main.py
│       ├── config.py
│       ├── constants.py
│       ├── data/
│       │   ├── __init__.py
│       │   ├── extractor.py
│       │   ├── providers/
│       │   │   ├── __init__.py
│       │   │   ├── yahoo.py
│       │   │   ├── alphavantage.py
│       │   │   └── other_provider.py
│       │   ├── loader.py
│       │   └── preprocess.py
│       ├── models/
│       │   ├── __init__.py
│       │   ├── price_series.py
│       │   └── portfolio.py
│       ├── analysis/
│       │   ├── __init__.py
│       │   ├── statistics.py
│       │   ├── montecarlo.py
│       │   └── reports.py
│       ├── visualization/
│       │   ├── __init__.py
│       │   └── plots.py
│       └── utils/
│           ├── __init__.py
│           ├── logger.py
│           └── helpers.py
└── tests/
    ├── test_extractor.py
    ├── test_price_series.py
    ├── test_portfolio.py
    └── test_montecarlo.py
```

## Architecture diagram

![Architecture diagram](docs/architecture_diagram.png)

## Requirements

- Python 3.10 or higher.
- Optional API keys (`ALPHAVANTAGE_API_KEY`) for providers that require them.

Quick install:

```bash
python -m venv .venv
. .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e .
# (optional) visualisation extras
pip install -e .[viz]
```

Launch the CLI:

```bash
miax-stock-toolkit --help
```

## Recommended workflow

1. **Configure providers** via environment variables or a `.env` file.
2. **Download series** with `miax-stock-toolkit fetch --provider yahoo --symbols AAPL,MSFT --start 2020-01-01 --end 2024-12-31`.
3. **Persist or reload** standardised data through `loader.py`.
4. **Preprocess** (cleaning, imputation, alignment) before any advanced analysis.
5. **Analyse** descriptive statistics and risk via the methods of `PriceSeries` and `Portfolio`.
6. **Simulate** forward scenarios with `miax-stock-toolkit montecarlo ...` or `Portfolio.run_monte_carlo()`.
7. **Generate reports** in Markdown with `miax-stock-toolkit report ...` and save charts via `--save-panel`.

## Configuration

`config.py` uses `pydantic-settings` to read environment variables, `.env` files and defaults. You can set the data storage path (`STOCK_TOOLKIT_DATA_DIR`) and API keys:

```bash
export ALPHAVANTAGE_API_KEY="my-key"
export STOCK_TOOLKIT_DATA_DIR="/path/to/data"
export STOCK_TOOLKIT_MAX_WORKERS=8
```

Quick `.env` setup — place at the project root:

```dotenv
# Alpha Vantage API key (optional, required by the alphavantage provider)
ALPHAVANTAGE_API_KEY=

# Base data folder (optional)
STOCK_TOOLKIT_DATA_DIR=./data

# Default provider (optional: yahoo | alphavantage | mock)
STOCK_TOOLKIT_DEFAULT_PROVIDER=yahoo
```

Recognised variables:

- `ALPHAVANTAGE_API_KEY` — Alpha Vantage API key.
- `STOCK_TOOLKIT_DATA_DIR` — base data folder.
- `STOCK_TOOLKIT_MAX_WORKERS` — concurrent-download thread cap.

## Data input contract (`PriceSeries`)

To guarantee consistency across providers and external sources, `PriceSeries` enforces:

- Index: monotonically increasing `DatetimeIndex`, no duplicates.
- Required columns: `open`, `high`, `low`, `close`, `adj_close`, `volume` (numeric; non-negative prices).
- Preprocessing helpers (`validate_price_series`, `align_series`, `fill_missing`, `resample_series`) make adapting external data straightforward.

To build a `PriceSeries` by hand:

```python
from stock_toolkit.models.price_series import PriceSeries
series = PriceSeries.from_dataframe("TICKER", df)
```

## CLI examples

Download stock or index series (e.g. `^GSPC`, `^IXIC`):

```bash
miax-stock-toolkit fetch --provider yahoo --symbols AAPL,^GSPC --start 2020-01-01 --end 2024-12-31 \
  --max-workers 8 --output ./data/processed/prices.parquet
```

Portfolio Markdown report (equal weights if not specified):

```bash
miax-stock-toolkit report --symbols AAPL,MSFT --provider yahoo --markdown-output ./data/reports/portfolio.md
```

Monte Carlo with panel export and no GUI window:

```bash
miax-stock-toolkit montecarlo --symbols AAPL,MSFT --provider yahoo --periods 252 --simulations 2000 \
  --save-panel ./data/reports/montecarlo_panel.png --no-show
```

Fundamentals snapshot and macro time series:

```bash
miax-stock-toolkit fundamentals --symbol AAPL --provider alphavantage --output ./data/processed/aapl_funda.parquet
miax-stock-toolkit macro --indicator CPI --provider alphavantage --output ./data/processed/cpi.parquet
```

## Extensibility

- Add a new provider by implementing the `BaseProvider` interface and registering it at runtime via `DataExtractor.register_provider(...)`, or by extending the factory `data.providers.create_default_providers(...)`.
- Models are dataclasses, which keep validation and derived computations close to the data.
- Analysis and visualisation modules are decoupled, making it easy to swap libraries (e.g. Plotly or Altair).

Data and portfolio policies worth noting:

- **Returns** — Monte Carlo uses log-returns. Portfolio metrics let you choose the return type (`return_type="simple"|"log"`) and default to log-returns.
- **Frequency** — every symbol must be unique within a portfolio. If you need the same series at a different frequency, resample it before adding it.

## Documentation and diagrams

- The architecture diagram in `docs/architecture_diagram.png` is generated with FossFLOW; the image is updated manually in this repository.
- FossFLOW is an open-source PWA for isometric diagrams. Built on top of React and the Isoflow library (forked and published on NPM as `fossflow`), it runs fully in the browser with offline support.

## License

This project is released under the MIT License. See `LICENSE` for details.
