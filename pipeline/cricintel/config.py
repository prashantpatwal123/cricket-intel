"""Filesystem layout. Override the root with CRICINTEL_DATA."""
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path(os.environ.get("CRICINTEL_DATA", REPO_ROOT / "data"))
RAW = DATA_ROOT / "raw"
CANONICAL = DATA_ROOT / "canonical"
METADATA = DATA_ROOT / "metadata"
MODELS = DATA_ROOT / "models"
DOCS_DATA = REPO_ROOT / "docs" / "data"
