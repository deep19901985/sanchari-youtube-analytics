"""Quality checks for Sanchari Day 3 all-video Analytics landing files.

This module deliberately does not call Google or Databricks: it validates
immutable local landing artifacts and is safe to import in CI.
"""

import json
import math
from datetime import date
from pathlib import Path

# Likes in daily YouTube Analytics can represent a net change, including
# removals of previous likes. Do not reject a negative daily likes value.
# Keep other collected metrics nonnegative unless source behaviour proves otherwise.
SIGNED_METRICS = {"likes"}

EXPECTED_METRICS = {
    "views", "estimatedMinutesWatched", "averageViewDuration",
    "likes", "comments", "shares",
}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def load_manifest(run_directory: Path) -> dict:
    """Read manifest and identify runs produced by the all-video extractor."""
    path = Path(run_directory) / "manifest.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    _require(isinstance(data, dict), f"Manifest must be a JSON object: {path}")
    return data


def is_all_video_run(manifest: dict) -> bool:
    """Ignore older single-video experiments with a different contract."""
    return "video_ids_requested" in manifest and "mode" in manifest


def validate_run(run_directory: Path) -> dict:
    """Validate a completed all-video run. Raise ValueError on any problem."""
    run_directory = Path(run_directory)
    manifest = load_manifest(run_directory)

    _require(is_all_video_run(manifest), f"Not an all-video run: {run_directory}")
    _require(manifest.get("status") == "completed", "Run status is not completed")
    _require(manifest.get("mode") in {"backfill", "incremental"}, "Invalid run mode")
    run_id = manifest.get("extract_run_id")
    channel_id = manifest.get("channel_id")
    _require(isinstance(run_id, str) and run_id == run_directory.name,
             "Run ID does not match directory name")
    _require(isinstance(channel_id, str) and bool(channel_id), "Missing channel ID")
    _require(manifest.get("report_timezone") == "America/Los_Angeles",
             "Unexpected report timezone")

    start = date.fromisoformat(manifest["report_start_date"])
    end = date.fromisoformat(manifest["report_end_date"])
    _require(start <= end, "Report start date occurs after end date")
    _require(isinstance(manifest.get("record_count"), int)
             and not isinstance(manifest["record_count"], bool)
             and manifest["record_count"] >= 0, "Invalid manifest record count")
    _require(isinstance(manifest.get("video_ids_requested"), int)
             and manifest["video_ids_requested"] > 0,
             "Invalid video count")

    headers = manifest.get("column_headers")
    _require(isinstance(headers, list), "Missing column headers")
    columns = [h["name"] for h in headers]
    _require(len(columns) == len(set(columns)), "Duplicate column headers")
    _require({"day", "video"}.issubset(columns), "Missing grain columns")
    _require(EXPECTED_METRICS.issubset(columns), "Missing expected metric columns")
    metric_columns = set(columns) - {"day", "video"}

    jsonl_path = run_directory / "video_daily.jsonl"
    seen = set()
    dates = []
    count = 0
    with jsonl_path.open("r", encoding="utf-8") as stream:
        for lineno, text in enumerate(stream, 1):
            _require(bool(text.strip()), f"Blank JSONL line {lineno}")
            row = json.loads(text)
            prefix = f"{jsonl_path.name} line {lineno}: "
            _require(row.get("extract_run_id") == run_id, prefix + "Run ID mismatch")
            _require(row.get("channel_id") == channel_id, prefix + "Channel mismatch")
            _require(row.get("source_endpoint") == "youtubeAnalytics.reports.query",
                     prefix + "Unexpected API endpoint")
            _require(bool(row.get("ingested_at_utc")), prefix + "Missing ingestion timestamp")
            video_id = row.get("video_id")
            _require(isinstance(video_id, str) and bool(video_id),
                     prefix + "Missing video ID")
            day = date.fromisoformat(row["reporting_date"])
            _require(start <= day <= end, prefix + "Date outside requested window")
            key = (video_id, day)
            _require(key not in seen, prefix + "Duplicate video-day key")
            seen.add(key)
            dates.append(day.isoformat())

            metrics = row.get("metrics")
            _require(isinstance(metrics, dict), prefix + "Metrics must be a dictionary")
            _require(set(metrics) == metric_columns, prefix + "Metric column mismatch")
            for name, value in metrics.items():
                _require(isinstance(value, (int, float)) and not isinstance(value, bool)
                         and math.isfinite(value),
                         prefix + f"Invalid numeric metric {name}: {value!r}")
                if name not in SIGNED_METRICS:
                    _require(value >= 0,
                             prefix + f"Invalid nonnegative metric {name}: {value!r}")

            raw = row.get("raw_row")
            _require(isinstance(raw, list) and len(raw) == len(columns),
                     prefix + "Raw row/header length mismatch")
            original = dict(zip(columns, raw))
            _require(original["day"] == row["reporting_date"]
                     and original["video"] == video_id,
                     prefix + "Raw dimension values mismatch")
            _require(all(original[name] == metrics[name] for name in metric_columns),
                     prefix + "Metrics do not match raw API row")
            count += 1

    _require(count == manifest["record_count"],
             f"Manifest has {manifest['record_count']} records; JSONL has {count}")
    _require(manifest.get("max_reported_date") == (max(dates) if dates else None),
             "Manifest max reported date mismatch")
    return {
        "run_id": run_id,
        "mode": manifest["mode"],
        "channel_id": channel_id,
        "report_end_date": end.isoformat(),
        "records": count,
        "unique_video_days": len(seen),
        "api_pages": manifest.get("api_pages"),
    }


def validate_checkpoint(checkpoint_path: Path, latest_result: dict) -> None:
    """Verify checkpoint points to a validated, completed all-video run."""
    state = json.loads(Path(checkpoint_path).read_text(encoding="utf-8"))
    _require(state.get("channel_id") == latest_result["channel_id"],
             "Checkpoint channel ID mismatch")
    _require(state.get("last_run_id") == latest_result["run_id"],
             "Checkpoint does not point to the latest validated run")
    _require(state.get("last_successful_requested_end_date")
             == latest_result["report_end_date"],
             "Checkpoint date does not match latest validated run")
