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
# Real data. Retrieved by the fetch-cricsheet GitHub workflow into branch data/cricsheet-raw, then:
git worktree add /tmp/csraw origin/data/cricsheet-raw
.venv/bin/python -m cricintel.sources.cricsheet import --src /tmp/csraw   # re-hashes, aborts on mismatch
.venv/bin/python -m cricintel.build --source cricsheet && .venv/bin/python -m cricintel.qa --dataset cricsheet
scripts/dev-up.sh cricsheet     # API + web in REAL_DATA mode
# Or the SYNTHETIC fixture (fictional players, for pipeline/UI testing only):
.venv/bin/python -m cricintel.sources.synthetic && .venv/bin/python -m cricintel.build --source synthetic
.venv/bin/python -m cricintel.qa --dataset synthetic
CRICINTEL_DATASET=synthetic .venv/bin/uvicorn cricintel.api:app --app-dir pipeline --port 8000
```

Data attribution: ball-by-ball data and player register from [Cricsheet](https://cricsheet.org). The Register is under the Open Data Commons
Attribution License; cricsheet.org states no licence for match data, so this is an internal preview until Cricsheet confirms terms
(see docs/data/cricsheet-verification.md).
