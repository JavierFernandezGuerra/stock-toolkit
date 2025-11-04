"""Generic helper utilities."""

from __future__ import annotations

from typing import Iterable, Sequence

import numpy as np


def normalize_weights(weights: Sequence[float]) -> np.ndarray:
    arr = np.asarray(weights, dtype=float)
    total = arr.sum()
    if total == 0:
        raise ValueError("Los pesos no pueden sumar cero")
    return arr / total


def chunked(iterable: Iterable, size: int):
    chunk = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) == size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


