# Sanchari — YouTube Analytics Data Engineering

An educational portfolio lakehouse: **YouTube APIs → JSON landing → Bronze Delta → Silver Delta/PySpark → Gold dbt → Power BI**, governed by Unity Catalog and orchestrated with Databricks Jobs.

> Status: Day 1 scaffold only. No YouTube API access, Databricks deployment, or actual pipeline execution has yet been configured. Do not describe this as a deployed production system.

## Day 1 goals
- [ ] Describe the end-to-end architecture and metric grains
- [ ] Execute `notebooks/00_workspace_validation.py` in Databricks
- [ ] Establish local Python 3.11+, virtual environment and Git
- [ ] Run tests locally
- [ ] Publish to a new GitHub repository, with secret scanning hygiene

## Local setup (Windows PowerShell)

Install Python 3.11 or 3.12, Git, and VS Code first. In this repository folder:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python scripts/check_local.py
pytest -q
```

If `py -3.11` is unavailable, run `py -0p` to view installed Python versions and use an available supported version (3.11+). If PowerShell activation is blocked, use `.venv\Scripts\python.exe` without activation, e.g. `.venv\Scripts\python.exe -m pytest -q`.

No Google API, Databricks, or dbt credentials are necessary for Day 1 local tests. OAuth clients and dbt adapter will be configured in later days, after validating the workspace.

## Databricks validation

1. Open an existing Free Edition workspace (or create one).
2. Create a Python notebook and paste the contents of `notebooks/00_workspace_validation.py`, or import it using your workspace's available import control.
3. Attach to the default **serverless** compute. Run the cells and record the outputs **without sharing workspace tokens, cookies or secrets**.
4. Verify availability of SQL Warehouses, Jobs, Pipelines, and Catalog Explorer via the UI. Document visible options in `docs/day1-validation.md`.
5. Do **not** create Azure paid compute or assume Academy Labs / classic clusters are available.

See `docs/architecture.md` for design, and `docs/day1-validation.md` for the results template.

## Repository structure

```text
.
├── .github/workflows/python-ci.yml   # Local-only CI on pull requests and pushes
├── .gitignore                         # Credential and data exclusions
├── .env.example                       # Variable names, not secrets
├── docs/
│   ├── architecture.md
│   └── day1-validation.md
├── notebooks/
│   └── 00_workspace_validation.py
├── scripts/
│   └── check_local.py
├── src/sanchari/
│   ├── __init__.py
│   └── quality.py
├── tests/test_quality.py
└── pyproject.toml
```

## Initial lakehouse contracts

- `bronze.video_metadata_raw`: one row per **API response record/ingestion**, raw payload plus ingestion metadata.
- `bronze.video_statistics_snapshot_raw`: one row per **video per snapshot timestamp** (cumulative counters).
- `bronze.video_daily_analytics_raw`: one row per **video-day (and any selected breakdowns)** per report extraction; backfill windows may overlap.
- `silver.dim_video`: one current record per video ID, with optional historical metadata later.
- `silver.fct_video_stats_snapshot`: one row per video ID / snapshot timestamp.
- `silver.fct_video_daily`: one row per video ID / day, for the exact selected report dimensions, with reconciled reruns.
- `gold.dim_video`, `gold.dim_date`, `gold.fct_video_daily`: star schema for analysis. Actual available columns depend on API access and dimensions selected.

## Design decisions and planned trade-offs

- **Local ingestion first**: Free Edition serverless outbound internet can be limited. The local process obtains OAuth access and writes JSONL artifacts, which are then uploaded to a Unity Catalog volume. Cloud ingestion is a later optional enhancement.
- **Raw replay**: preserve source JSON, `ingested_at_utc`, `source_endpoint`, `extract_run_id`, and report window.
- **Daily Analytics != lifetime statistics**: never subtract or sum incompatible metrics without clarifying provenance.
- **Idempotency**: persist run metadata and MERGE by business grain in Silver; overlap the trailing Analytics window when late updates are plausible.
- **Quality**: duplicate-grain tests, not-null keys, valid date ranges, nonnegative metrics; quarantine malformed records.
- **Secrets**: use OAuth and local gitignored credential storage; never commit Google client secrets, refresh tokens, access tokens, `.env`, data extracts or `.databrickscfg`.
- **Professional presentation**: show architecture, tests, operational design and limitations; do not claim SLA-backed production deployment from Free Edition.

## Planned 12-day scope (~66 focused hours)

1. Architecture, environment, Python & GitHub
2. Google Cloud project, OAuth setup and first YouTube Data API extraction
3. YouTube Analytics API, incremental capture and landing data contracts
4. Bronze ingestion & Delta raw tables
5. Silver PySpark cleanup, schema handling and deduplication
6. Incremental MERGE, watermarks, reprocessing and checks
7. dbt Core setup, Databricks adapter, staging models
8. Dimensional Gold models, dbt generic and custom tests
9. Lakeflow/Auto Loader evaluation and scheduled orchestration
10. Monitoring, error recovery, cost/performance practices
11. Power BI dashboard, KPIs and documentation
12. GitHub Actions, end-to-end demo, validation, interview narrative

The precise ordering can be adjusted when features are unavailable.

## References

- Databricks Free Edition: https://docs.databricks.com/aws/en/getting-started/free-edition
- Free Edition limits: https://docs.databricks.com/aws/en/getting-started/free-edition-limitations
- Unity Catalog volume uploads: https://docs.databricks.com/aws/en/volumes/volume-files
- YouTube Analytics query: https://developers.google.com/youtube/analytics/reference/reports/query
- dbt Databricks setup: https://docs.getdbt.com/docs/local/connect-data-platform/databricks-setup
