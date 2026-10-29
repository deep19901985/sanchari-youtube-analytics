"""Backfill older YouTube Analytics dates WITHOUT altering the incremental checkpoint.

Examples (run from repository root):
  python scripts/backfill_historical_analytics.py --start 2023-01-01 --end 2023-03-31
  python scripts/backfill_historical_analytics.py --start 2023-01-01 --end 2026-07-25

A second run skips windows with already-validated landing files for the
same channel and video inventory. Source API access is only needed for new windows.
"""
import argparse
import hashlib
import json
import shutil
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from googleapiclient.discovery import build

from check_youtube_connection import authenticate
from extract_all_video_analytics import ANALYTICS_LANDING, fetch_rows, load_videos
from sanchari.analytics_quality import validate_run
from sanchari.history import chunk_date_ranges


def video_inventory_hash(video_ids):
    return hashlib.sha256("\n".join(sorted(video_ids)).encode("utf-8")).hexdigest()


def find_existing_window(channel_id, fingerprint, start, end):
    """Resume only if previous matching extraction passes its validator."""
    if not ANALYTICS_LANDING.exists():
        return None
    for path in sorted(ANALYTICS_LANDING.iterdir()):
        manifest_file = path / "manifest.json"
        if not path.is_dir() or not manifest_file.exists():
            continue
        try:
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        if not all((
            manifest.get("status") == "completed",
            manifest.get("mode") == "backfill",
            manifest.get("historical_backfill") is True,
            manifest.get("channel_id") == channel_id,
            manifest.get("video_inventory_sha256") == fingerprint,
            manifest.get("report_start_date") == start.isoformat(),
            manifest.get("report_end_date") == end.isoformat(),
        )):
            continue
        validate_run(path)  # Do not trust manifest alone.
        return path
    return None


def save_window(records, headers, pages, channel_id, video_ids, video_manifest,
                fingerprint, start, end):
    """Write a validated immutable landing folder, then make it visible atomically."""
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid4().hex[:8]
    timestamp = datetime.now(timezone.utc).isoformat()
    ANALYTICS_LANDING.mkdir(parents=True, exist_ok=True)
    final_path = ANALYTICS_LANDING / run_id

    # Temporary directory is OUTSIDE the scanned landing directory so a crash
    # cannot leave a broken run that the existing validator would try to load.
    state_dir = ANALYTICS_LANDING.parent / "_pending_analytics_runs"
    state_dir.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="history_", dir=state_dir))
    try:
        with (temporary / "video_daily.jsonl").open("w", encoding="utf-8") as stream:
            for record in records:
                stream.write(json.dumps({
                    "extract_run_id": run_id,
                    "ingested_at_utc": timestamp,
                    "source_endpoint": "youtubeAnalytics.reports.query",
                    "channel_id": channel_id,
                    **record,
                }, ensure_ascii=False) + "\n")
        manifest = {
            "extract_run_id": run_id,
            "extracted_at_utc": timestamp,
            "channel_id": channel_id,
            "mode": "backfill",  # Compatible with existing quality validator.
            "historical_backfill": True,
            "video_inventory_sha256": fingerprint,
            "report_start_date": start.isoformat(),
            "report_end_date": end.isoformat(),
            "report_timezone": "America/Los_Angeles",
            "video_ids_requested": len(video_ids),
            "day2_missing_video_ids": video_manifest.get("missing_video_ids", []),
            "api_pages": pages,
            "record_count": len(records),
            "column_headers": headers,
            "max_reported_date": max((row["reporting_date"] for row in records), default=None),
            "status": "completed",
        }
        (temporary / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8")
        # validate_run requires dirname == run_id.
        temp_named = temporary.parent / run_id
        temporary.rename(temp_named)
        temporary = temp_named
        validate_run(temporary)
        temporary.rename(final_path)
        return final_path
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", required=True, type=date.fromisoformat,
                        help="First date inclusive, YYYY-MM-DD")
    parser.add_argument("--end", required=True, type=date.fromisoformat,
                        help="Last date inclusive, YYYY-MM-DD")
    parser.add_argument("--chunk-days", type=int, default=90,
                        help="Maximum requested days per batch (default 90)")
    args = parser.parse_args()

    windows = list(chunk_date_ranges(args.start, args.end, args.chunk_days))
    # This uses same five-day buffer as the existing incremental pipeline.
    cutoff = datetime.now(timezone.utc).date() - timedelta(days=5)
    if args.end > cutoff:
        parser.error(f"--end must be on or before {cutoff}, the five-day buffer")

    channel, video_ids, video_manifest = load_videos()
    channel_id = channel["id"]
    fingerprint = video_inventory_hash(video_ids)
    print("Channel:", channel.get("snippet", {}).get("title", "Unknown"))
    print("Channel ID:", channel_id)
    print("Video IDs:", len(video_ids))
    print("Historical windows:", len(windows))
    print("Incremental checkpoint will NOT be modified.")

    client = None
    processed = skipped = total_rows = 0
    for index, (start, end) in enumerate(windows, 1):
        prior = find_existing_window(channel_id, fingerprint, start, end)
        if prior is not None:
            print(f"[{index}/{len(windows)}] SKIP {start} to {end}: validated {prior.name}")
            skipped += 1
            continue
        print(f"[{index}/{len(windows)}] FETCH {start} to {end}", flush=True)
        if client is None:
            client = build("youtubeAnalytics", "v2",
                           credentials=authenticate(), cache_discovery=False)
        records, headers, pages = fetch_rows(client, channel_id, video_ids, start, end)
        directory = save_window(records, headers, pages, channel_id, video_ids,
                                video_manifest, fingerprint, start, end)
        print(f"SAVED {len(records)} records, {pages} API pages: {directory.name}", flush=True)
        processed += 1
        total_rows += len(records)

    print(f"Completed: {processed} new windows; {skipped} existing windows skipped; "
          f"{total_rows} new video-day records")
    print("Checkpoint unchanged. Historical source coverage depends on current video inventory.")


if __name__ == "__main__":
    main()
