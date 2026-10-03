"""Tests run against an isolated small dataset in a temp dir (never the repo's data/ or docs/)."""
import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="cricintel-test-"))
os.environ["CRICINTEL_DATA"] = str(_TMP / "data")
os.environ["CRICINTEL_DOCS"] = str(_TMP / "docs")

import pytest  # noqa: E402

from cricintel import build  # noqa: E402
from cricintel.config import RAW  # noqa: E402
from cricintel.sources import synthetic  # noqa: E402


@pytest.fixture(scope="session")
def dataset():
    synthetic.generate(scale=0.08, seed=11)
    build.build("synthetic")
    from cricintel.db import connect
    return connect("synthetic")


@pytest.fixture
def raw_dir():
    return RAW / "synthetic"
