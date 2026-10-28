# Day 3 — YouTube Analytics API and incremental landing validation

## Run evidence (28 October 2026)

- **Channel:** `sanchari.travelshorts` (`UCGpXEis-qat1YG04joiG_Vw`)
- **Video IDs loaded from Day 2:** 1,247
- **Backfill:** 2026-07-26 through 2026-10-23; 3,116 video-day records; 53 successfully retrieved API pages; run `20261028T210824Z_c1db3000`.
- **Incremental rerun:** 2026-10-10 through 2026-10-23; 535 video-day records; 27 successfully retrieved API pages; run `20261028T211355Z_70589085`.
- **Checkpoint:** `data/state/video_daily_checkpoint.json` (ignored by Git).
- **Landing:** `data/landing/youtube_analytics_api/<run_id>/` (ignored by Git).

## Data contract

All-video landing rows include `extract_run_id`, `ingested_at_utc`, `source_endpoint`, `channel_id`, `reporting_date`, `video_id`, `metrics`, and `raw_row`. Each run has a `manifest.json` containing run identity, reporting window, headers, record count, and provenance.

Grain within one run: `(video_id, reporting_date)`. **Rows across runs overlap intentionally** as the pipeline re-requests late-changing reporting days. Reconcile overlaps by business key and chosen report run during Silver processing; never add together the raw run counts to compute unique performance.

## Correctness finding: daily likes can be negative

A production-like historical run returned `likes: -1`. This is an allowed
net daily likes change when a previous like is removed. The first version of
the validator rejected all negative metrics, which was too strict.
The corrected validator permits negative `likes` while requiring finite numeric
values and retaining nonnegative checks for views, watch time, duration,
comments and shares. The raw JSONL must **not** be changed to hide this case.
This is a useful source-semantic quality rule, not evidence of corrupt data.

## Quality controls

Run `python scripts/validate_youtube_analytics_landing.py` to check each full-channel run's manifest, reporting window, schema, record count, channel, raw-row consistency, unique video-day keys, and current checkpoint. Execute `pytest -q` to test the validator offline.

The initial 90-day backfill has **not** recovered analytics from all historical reporting dates. The Day 2 extraction also reported at least one missing video detail, so complete video metadata coverage is not yet proven. Classification of Shorts remains a separate Silver-stage task: duration alone is insufficient.

## Implementation constraints

- The API reports in **America/Los_Angeles** reporting dates; this is not local UK time.
- A full response page may conceal further rows, so the extractor recursively bisects date windows rather than relying on second-page pagination, which previously returned HTTP 500.
- The checkpoint is updated after successful extraction and file writes. The stored date represents the last *requested* report end date, not the last nonzero activity date.
- The API page counts exclude internal retries, so they are **not** exact HTTP request counts or a benchmark of latency/cost.
- Secrets and `data/` are excluded by `.gitignore` and must never be committed.

## Remaining work

- [ ] Execute landing-data validator locally and record its output.
- [ ] Execute project tests and verify GitHub Actions after commit.
- [ ] Investigate missing video metadata from Day 2.
- [ ] Build Bronze Delta ingestion in Databricks on Day 4.
