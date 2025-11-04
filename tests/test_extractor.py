from __future__ import annotations

from stock_toolkit.data.extractor import DataExtractor
from stock_toolkit.data.providers.other_provider import MockProvider


def test_extractor_fetch_many_mock():
    extractor = DataExtractor(providers={"mock": MockProvider()}, default_provider="mock")
    series_list = extractor.fetch_many(["AAA", "BBB"], periods=30, seed=1)
    assert len(series_list) == 2
    assert all(series.prices.shape[0] == 30 for series in series_list)


