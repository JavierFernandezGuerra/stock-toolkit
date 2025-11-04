"""Utilities to persist and load price series."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from ..models.price_series import PriceSeries


class DataLoader:
    """Handles persistence of PriceSeries objects."""

    def __init__(self, base_dir: Path | str) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_price_series(
        self,
        series_list: Iterable[PriceSeries],
        output_path: Path | None = None,
        fmt: str | None = None,
    ) -> Path:
        if output_path is None:
            output_path = self.base_dir / "price_series.parquet"

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        frames = []
        for series in series_list:
            frame = series.to_dataframe()
            frame.insert(0, "symbol", series.symbol)
            frames.append(frame)

        combined = pd.concat(frames)

        fmt = fmt or output_path.suffix.lower()
        if fmt in {".parquet", "parquet"}:
            combined.to_parquet(output_path)
        elif fmt in {".csv", "csv"}:
            combined.to_csv(output_path)
        else:
            raise ValueError(f"Formato no soportado: {fmt}")

        return output_path

    def load_price_series(self, path: Path | str) -> list[PriceSeries]:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(path)

        if path.suffix.lower() == ".parquet":
            frame = pd.read_parquet(path)
        elif path.suffix.lower() == ".csv":
            frame = pd.read_csv(path, index_col=0, parse_dates=True)
        else:
            raise ValueError("Formato desconocido para cargar series")

        series_list = []
        for symbol_key, group in frame.groupby("symbol"):
            symbol = str(symbol_key)
            group = group.drop(columns=["symbol"])
            series_list.append(PriceSeries.from_dataframe(symbol=symbol, data=group))
        return series_list
