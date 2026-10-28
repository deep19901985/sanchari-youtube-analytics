# Day 1 — environment evidence log

**Date:** 2026-10-28
**Databricks cloud displayed in workspace:** not checked
**Workspace URL (hostname only; never credentials):** not checked

| Check | Expected / action | Actual result | Status |
|---|---|---|---|
| Free Edition workspace sign-in | Opens successfully | — | Pending |
| Notebook runtime | Python and PySpark are usable | — | Pending |
| SQL execution | `SELECT current_catalog()` works | — | Pending |
| Unity Catalog | `SHOW CATALOGS` returns accessible catalogs | — | Pending |
| Permissions | Able to use/create appropriate Sanchari schema/volume | — | Pending |
| Serverless SQL Warehouse | Connection details available | — | Pending |
| Lakeflow pipelines | Menu and create access visible | — | Pending |
| Databricks Jobs | Menu and create access visible | — | Pending |
| Python local environment | Python >=3.11, pip works | — | Pending |
| Git | `git --version` works | — | Pending |
| Unit tests | `pytest -q` succeeds | — | Pending |
| GitHub | New repository exists and CI runs | — | Pending |

## Notes / limitations found

- 

## Decisions

- Data ingestion runtime: local Python first, as Free Edition egress limits may affect direct API calls.
- Landing target: Unity Catalog volume if authorized; use workspace UI upload for Day 2/3 prototype.
- Do not create cloud resources or billable infrastructure just to pass a feature check.
