# cricket-intel (internal working name)

Consumer cricket intelligence platform: **Data → Visualization → Prediction**, with mandatory provenance
(OBSERVED · DERIVED · RECONSTRUCTED · MODELLED · ILLUSTRATIVE) on every statistic, graphic and prediction.

- `docs/00-feasibility-report.md`: approved feasibility & design report (Phase 0)
- `docs/data/cricsheet-verification.md`: what is verified vs assumed about Cricsheet
- `pipeline/`: Python ingestion → canonical Parquet → DuckDB analytics → FastAPI
- `web/`: Next.js mobile-first app

## Quick start

```bash
python3 -m venv .venv && .venv/bin/pip install -e pipeline[dev]
# Real data (requires network access to cricsheet.org):
.venv/bin/python -m cricintel.sources.cricsheet verify      # downloads + records verification
.venv/bin/python -m cricintel.build --source cricsheet
# Or the SYNTHETIC fixture (fictional players, for pipeline/UI testing only):
.venv/bin/python -m cricintel.sources.synthetic && .venv/bin/python -m cricintel.build --source synthetic
.venv/bin/python -m cricintel.qa --dataset synthetic
CRICINTEL_DATASET=synthetic .venv/bin/uvicorn cricintel.api:app --app-dir pipeline --port 8000
```

Data attribution: ball-by-ball data from [Cricsheet](https://cricsheet.org), Open Data Commons Attribution License
(pending primary verification; see docs).
