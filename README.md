# Sanchari — YouTube Analytics Data Engineering

A portfolio-scale YouTube Analytics lakehouse based on data from the **Sanchari** channel. The implemented engineering stack includes Python, the YouTube Data and Analytics APIs, PySpark, Delta Lake, Unity Catalog and Databricks. The target architecture adds **dbt Core, Gold dimensional models, Databricks Jobs and Power BI**, with a separate Microsoft Fabric / DP-600 learning track.

> **Project status — 15 November 2026:** Local YouTube API extraction, JSONL landing, Bronze Delta and Silver Delta processing have been implemented and exercised. Data-quality and repeat-MERGE checks have passed. **dbt Gold, scheduled Jobs, Power BI reporting and Microsoft Fabric implementation remain planned.** This is a working educational/portfolio pipeline, not an enterprise production deployment.

## Architecture and status

```text
YouTube Data API + YouTube Analytics API
           |
           v
Local Python extraction, OAuth, JSONL + run manifests          [IMPLEMENTED]
           |
           v
Unity Catalog Volume landing                                  [IMPLEMENTED]
           |
           v
Bronze Delta: raw video-day JSON and ingestion lineage        [IMPLEMENTED]
           |
           v
Silver Delta: PySpark validation, deduplication, MERGE         [IMPLEMENTED]
           |
           v
dbt staging + Gold dimensional models                         [PLANNED]
           |
           v
Power BI semantic model and analytics dashboard               [PLANNED]

Databricks Jobs / scheduling and monitoring                    [PLANNED]
GitHub Actions: Python unit tests                              [IMPLEMENTED]
Microsoft Fabric / DP-600 practical track                      [PLANNED — ACCESS TO CHECK]
```

See [architecture documentation](docs/architecture.md) for the intended end-to-end design. It includes some planned components that are not yet deployed.

## Verified Databricks processing

Results below were observed in the Databricks notebooks on **15 November 2026**. They are point-in-time observations, not live reporting figures.

| Check | Result |
| --- | ---: |
| Bronze video-day rows | 37,327 |
| Valid rows entering Silver deduplication | 37,327 |
| Unique Silver video-day rows | 36,251 |
| Overlapping extraction rows reconciled | 1,076 |
| Quarantined rows | 0 |
| Duplicate Silver business-key groups | 0 |
| Null Silver business-key rows | 0 |
| Disallowed negative metric rows | 0 |
| Valid Silver observations with negative daily likes | 330 |
| Silver acceptance tests | PASS |

The Silver business key is **`(channel_id, video_id, reporting_date)`**. The transformation uses a PySpark window to choose a version for each key, then a Delta `MERGE` to insert new keys and update qualifying newer records. On 15 November, repeated unchanged MERGEs (Delta versions 4 and 5) reported **zero inserted, updated and deleted rows**, establishing idempotent writes for that input.

**Scope distinction:** The current Silver code **rescans all Bronze rows** before the MERGE. Although the output is repeatable and the extractor supports incremental API windows, fully incremental *Bronze-to-Silver source consumption* with watermarks or change tracking has **not** been implemented.

## Implemented work

### API extraction and JSONL landing

Local Python scripts access the YouTube APIs using OAuth, write video/analytics extraction outputs with run manifests and provenance, support historical backfills, and maintain an incremental extraction checkpoint. Overlapping report windows are expected because historical YouTube Analytics metrics can change. See [Day 3 validation notes](docs/day3-validation.md).

### Bronze — raw, traceable observations

[Bronze ingestion notebook](databricks/01_bronze_youtube_ingestion..ipynb) imports landed video-day JSONL from a Unity Catalog volume, preserves the original JSON and source file/run fields, and uses an **insert-only Delta MERGE** keyed by run, video and reporting date to avoid duplicate ingestion on a rerun.

Table: `workspace.sanchari_bronze.youtube_video_daily_raw`.

### Silver — cleaned, deduplicated observations

[Silver processing notebook](databricks/02_silver_youtube_daily.ipynb) parses nested metrics, normalizes types, resolves missing channel IDs using same-video mapping evidence, validates record quality, selects winners from overlapping source extracts, and applies a conditional Delta MERGE.

Tables: `workspace.sanchari_silver.youtube_video_daily` and `workspace.sanchari_silver.youtube_video_daily_quarantine`.

Negative daily **likes** are allowed because a daily net change can be negative; views, watch time, duration, comments and shares are checked for invalid negative values. Rejected rows receive a reason and are written to the Silver quarantine table. The quarantine table is derived output, not a modification of Bronze.

### Automated Python testing

The repository includes tests for local extraction, history and quality logic. The [GitHub Actions Python workflow](.github/workflows/python-ci.yml) runs unit tests on pushes and pull requests. The [run associated with the Silver notebook commit](https://github.com/deep19901985/sanchari-youtube-analytics/actions/runs/43698675658) completed successfully on 15 November 2026. **This CI run does not execute the Databricks notebooks.**

## Repository guide

| Path | Purpose |
| --- | --- |
| `databricks/01_bronze_youtube_ingestion..ipynb` | Bronze Delta ingestion and rerun test |
| `databricks/02_silver_youtube_daily.ipynb` | Silver PySpark parsing, quality, deduplication and MERGE |
| `scripts/` | Local YouTube API checks, extraction, backfills and landing validation |
| `src/sanchari/` | Shared Python ingestion, history and validation modules |
| `tests/` | Python unit tests |
| `docs/` | Architecture and validation evidence |
| `.github/workflows/python-ci.yml` | CI for local Python tests |

## Local Python setup

From the repository root in Windows PowerShell, with Python 3.11 installed:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
pytest -q
```

If activation is blocked, use `.venv\Scripts\python.exe -m pytest -q`. API extraction requires a correctly configured, locally protected OAuth client and permissions; **never commit tokens, client secrets, `.env` files or raw extracts**. Databricks notebooks require their expected tables and landing files; importing a notebook alone does not reproduce these results.

## Remaining roadmap: Sanchari + DP-600

| Day | Sanchari portfolio (Databricks/dbt/Power BI) | Microsoft Fabric / DP-600 parallel learning |
| --- | --- | --- |
| 1–5 | API extraction, Bronze and initial Silver built | Not started |
| 6 | Silver quality and idempotency checks verified; document and publish work | Compare Fabric Lakehouse and Delta operations; check Fabric access |
| 7 | dbt Core setup and staging models | Try Fabric workspace/lakehouse and SQL if access is available |
| 8 | Gold star schema and dbt tests | Build a small Sanchari Fabric star schema, if possible |
| 9 | Databricks Jobs and orchestration | Fabric Data Pipelines and notebook scheduling |
| 10 | Power BI dashboard | Semantic models, DAX, relationships, storage modes |
| 11 | Monitoring, reliability and optimisation | RLS, performance, refresh, Direct Lake concepts |
| 12 | CI, documentation, end-to-end demo and interviews | Fabric security, governance, deployment, practice assessment |

Follow Day 12 with **dedicated DP-600 revision and mock assessments**. A Fabric exercise is only marked implemented once actually executed and validated; Microsoft Learn study alone is not a deployed Fabric solution.

## Current limitations and next engineering improvements

- Bronze-to-Silver reads currently scan all Bronze rows; add a safe watermark/change-data strategy and tests for late updates.
- Validate retries, failure recovery, scheduling and monitoring in the actual Databricks environment before claiming production-style orchestration.
- dbt models, a tested Gold star schema and the Power BI semantic model/dashboard are not yet present.
- Fabric access was previously blocked; availability must be verified before attempting implementation.
- YouTube Analytics daily measures and cumulative YouTube Data API counters have different semantics; avoid aggregating them as though they are interchangeable.
- Some planned architectures and data contracts are documented but have not yet been exercised. Do not claim an SLA-backed production deployment from this portfolio project.

## Useful references

- [YouTube Analytics reporting API](https://developers.google.com/youtube/analytics/reference/reports/query)
- [Databricks Free Edition](https://docs.databricks.com/aws/en/getting-started/free-edition)
- [Unity Catalog volumes](https://docs.databricks.com/aws/en/volumes/volume-files)
- [dbt Databricks setup](https://docs.getdbt.com/docs/local/connect-data-platform/databricks-setup)
- [Microsoft DP-600 study guide](https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/dp-600)
