"""Validate all Day 3 all-video landing runs and the current checkpoint.

Run from repository root after installing the editable project:
    python scripts/validate_youtube_analytics_landing.py
"""

from pathlib import Path

from sanchari.analytics_quality import (
    is_all_video_run, load_manifest, validate_checkpoint, validate_run,
)

ROOT = Path(__file__).resolve().parents[1]
LANDING = ROOT / "data" / "landing" / "youtube_analytics_api"
CHECKPOINT = ROOT / "data" / "state" / "video_daily_checkpoint.json"


def main():
    runs = []
    skipped = 0
    for directory in sorted(LANDING.iterdir()):
        if not directory.is_dir():
            continue
        # Previous single-video experiments use a different data contract.
        manifest = load_manifest(directory)
        if not is_all_video_run(manifest):
            skipped += 1
            continue
        result = validate_run(directory)
        runs.append(result)
        print(f"PASS {result['mode']:11s} {result['run_id']} — "
              f"{result['records']} unique video-day records")

    if not runs:
        raise ValueError("No Day 3 all-video runs found to validate")
    channel_ids = {r["channel_id"] for r in runs}
    if len(channel_ids) != 1:
        raise ValueError("Different channels found in all-video runs")

    latest = max(runs, key=lambda r: r["run_id"])
    validate_checkpoint(CHECKPOINT, latest)
    print("PASS checkpoint ->", latest["run_id"])
    print(f"VALIDATION PASSED: {len(runs)} complete run(s), "
          f"{skipped} single-video experiment(s) skipped")
    print("Note: overlaps across runs are expected; do not sum raw row counts.")


if __name__ == "__main__":
    main()
