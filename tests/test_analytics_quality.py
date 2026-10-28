"""Pure, offline tests for the Day 3 landing data contract."""

import json
from copy import deepcopy

import pytest

from sanchari.analytics_quality import validate_checkpoint, validate_run

HEADERS = [
    {"name": name}
    for name in [
        "day", "video", "views", "estimatedMinutesWatched",
        "averageViewDuration", "likes", "comments", "shares",
    ]
]


def sample_run(tmp_path):
    run_id = "20261028T211355Z_example"
    folder = tmp_path / run_id
    folder.mkdir()
    row = {
        "extract_run_id": run_id,
        "ingested_at_utc": "2026-10-28T21:13:55+00:00",
        "source_endpoint": "youtubeAnalytics.reports.query",
        "channel_id": "channel-1",
        "reporting_date": "2026-10-18",
        "video_id": "video-1",
        "metrics": {
            "views": 4, "estimatedMinutesWatched": 2,
            "averageViewDuration": 30, "likes": 1,
            "comments": 0, "shares": 0,
        },
        "raw_row": ["2026-10-18", "video-1", 4, 2, 30, 1, 0, 0],
    }
    manifest = {
        "extract_run_id": run_id,
        "channel_id": "channel-1",
        "mode": "incremental",
        "report_start_date": "2026-10-10",
        "report_end_date": "2026-10-23",
        "report_timezone": "America/Los_Angeles",
        "video_ids_requested": 1247,
        "record_count": 1,
        "column_headers": HEADERS,
        "max_reported_date": "2026-10-18",
        "status": "completed",
    }
    write_run(folder, manifest, [row])
    return folder, manifest, row


def write_run(folder, manifest, rows):
    (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (folder / "video_daily.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )


def test_valid_run(tmp_path):
    folder, _, _ = sample_run(tmp_path)
    assert validate_run(folder)["records"] == 1


def test_duplicate_video_day_rejected(tmp_path):
    folder, manifest, row = sample_run(tmp_path)
    manifest["record_count"] = 2
    write_run(folder, manifest, [row, deepcopy(row)])
    with pytest.raises(ValueError, match="Duplicate video-day"):
        validate_run(folder)


def test_manifest_count_mismatch_rejected(tmp_path):
    folder, manifest, row = sample_run(tmp_path)
    manifest["record_count"] = 2
    write_run(folder, manifest, [row])
    with pytest.raises(ValueError, match="Manifest has"):
        validate_run(folder)


def test_wrong_channel_rejected(tmp_path):
    folder, manifest, row = sample_run(tmp_path)
    row["channel_id"] = "other-channel"
    write_run(folder, manifest, [row])
    with pytest.raises(ValueError, match="Channel mismatch"):
        validate_run(folder)


def test_out_of_range_date_rejected(tmp_path):
    folder, manifest, row = sample_run(tmp_path)
    row["reporting_date"] = "2026-09-01"
    row["raw_row"][0] = "2026-09-01"
    write_run(folder, manifest, [row])
    with pytest.raises(ValueError, match="outside requested window"):
        validate_run(folder)


def test_negative_views_rejected(tmp_path):
    folder, manifest, row = sample_run(tmp_path)
    row["metrics"]["views"] = -1
    row["raw_row"][2] = -1
    write_run(folder, manifest, [row])
    with pytest.raises(ValueError, match="Invalid nonnegative metric"):
        validate_run(folder)


def test_negative_likes_allowed(tmp_path):
    # Removing an earlier like can create a negative net daily likes value.
    folder, manifest, row = sample_run(tmp_path)
    row["metrics"]["likes"] = -1
    row["raw_row"][5] = -1
    write_run(folder, manifest, [row])
    assert validate_run(folder)["records"] == 1


def test_negative_shares_rejected(tmp_path):
    folder, manifest, row = sample_run(tmp_path)
    row["metrics"]["shares"] = -1
    row["raw_row"][7] = -1
    write_run(folder, manifest, [row])
    with pytest.raises(ValueError, match="Invalid nonnegative metric shares"):
        validate_run(folder)


def test_nonnumeric_likes_rejected(tmp_path):
    folder, manifest, row = sample_run(tmp_path)
    row["metrics"]["likes"] = "-1"
    row["raw_row"][5] = "-1"
    write_run(folder, manifest, [row])
    with pytest.raises(ValueError, match="Invalid numeric metric likes"):
        validate_run(folder)


def test_raw_row_mismatch_rejected(tmp_path):
    folder, manifest, row = sample_run(tmp_path)
    row["raw_row"][2] = 100
    write_run(folder, manifest, [row])
    with pytest.raises(ValueError, match="Metrics do not match"):
        validate_run(folder)


def test_checkpoint_matches_completed_run(tmp_path):
    folder, _, _ = sample_run(tmp_path)
    result = validate_run(folder)
    state = {
        "channel_id": "channel-1",
        "last_run_id": result["run_id"],
        "last_successful_requested_end_date": "2026-10-23",
    }
    p = tmp_path / "checkpoint.json"
    p.write_text(json.dumps(state), encoding="utf-8")
    validate_checkpoint(p, result)


def test_checkpoint_mismatch_rejected(tmp_path):
    folder, _, _ = sample_run(tmp_path)
    result = validate_run(folder)
    state = {
        "channel_id": "channel-1",
        "last_run_id": "wrong-run",
        "last_successful_requested_end_date": "2026-10-23",
    }
    p = tmp_path / "checkpoint.json"
    p.write_text(json.dumps(state), encoding="utf-8")
    with pytest.raises(ValueError, match="Checkpoint does not point"):
        validate_checkpoint(p, result)


def test_empty_run_valid_when_manifest_matches(tmp_path):
    folder, manifest, _ = sample_run(tmp_path)
    manifest["record_count"] = 0
    manifest["max_reported_date"] = None
    write_run(folder, manifest, [])
    assert validate_run(folder)["records"] == 0
