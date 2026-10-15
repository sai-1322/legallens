import dataclasses
from pathlib import Path

import pytest

from legallens.config import get_settings
from legallens.pipeline import Pipeline

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "data" / "raw"


@pytest.fixture(scope="session")
def cfg():
    return get_settings()


@pytest.fixture(scope="session")
def pipe(cfg):
    return Pipeline(cfg)


@pytest.fixture
def make_cfg(cfg, tmp_path):
    def _make(**kw):
        kw.setdefault("data_dir", tmp_path)
        kw.setdefault("results_dir", tmp_path / "results")
        return dataclasses.replace(cfg, **kw)
    return _make
