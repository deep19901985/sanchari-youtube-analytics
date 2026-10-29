"""Validate all Day 3 all-video landing runs and the checkpoint it references."""

import json
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

    # Historical backfills created later should not advance the incremental
    # checkpoint. Verify the particular validated run that the checkpoint names.
    state = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
    checkpoint_run = next((r for r in runs if r["run_id"] == state.get("last_run_id")), None)
    if checkpoint_run is None:
        raise ValueError("Checkpoint does not point to any validated run")
    validate_checkpoint(CHECKPOINT, checkpoint_run)
    print("PASS checkpoint ->", checkpoint_run["run_id"])
    print(f"VALIDATION PASSED: {len(runs)} complete run(s), "
          f"{skipped} single-video experiment(s) skipped")
    print("Note: overlaps across runs are expected; do not sum raw row counts.")


if __name__ == "__main__":
    main()
