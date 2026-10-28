"""Day 3: incremental, all-video YouTube Analytics extraction."""

import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from check_youtube_connection import authenticate

ROOT = Path(__file__).resolve().parents[1]
VIDEO_LANDING = ROOT / "data" / "landing" / "youtube_data_api"
ANALYTICS_LANDING = ROOT / "data" / "landing" / "youtube_analytics_api"
CHECKPOINT = ROOT / "data" / "state" / "video_daily_checkpoint.json"
METRICS = "views,estimatedMinutesWatched,averageViewDuration,likes,comments,shares"
BATCH_SIZE = 50
PAGE_SIZE = 200


def load_videos():
    """Load IDs and channel identity from the latest completed Day 2 run."""
    for file in sorted(VIDEO_LANDING.glob("*/videos.jsonl"), reverse=True):
        channel_file = file.parent / "channel.json"
        manifest_file = file.parent / "manifest.json"
        if not (channel_file.exists() and manifest_file.exists()):
            continue
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        if manifest.get("status") != "completed":
            continue
        channel = json.loads(channel_file.read_text(encoding="utf-8"))
        channel_id = channel["id"]
        ids = []
        with file.open(encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    record = json.loads(line)
                    if record.get("channel_id") != channel_id:
                        raise ValueError("Video belongs to a different channel")
                    ids.append(record["video_id"])
        if ids:
            return channel, list(dict.fromkeys(ids)), manifest
    raise FileNotFoundError("No completed Day 2 video landing run found")


def select_window(channel_id, end_date):
    """First run: 90 days; subsequent runs: 14-day overlap."""
    if CHECKPOINT.exists():
        state = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
        if state["channel_id"] != channel_id:
            raise ValueError("Checkpoint channel does not match Day 2 data")
        previous_end = date.fromisoformat(state["last_successful_requested_end_date"])
        start_date = previous_end - timedelta(days=13)
        mode = "incremental"
    else:
        start_date = end_date - timedelta(days=89)
        mode = "backfill"
    if start_date > end_date:
        raise ValueError("Checkpoint is ahead of the requested reporting window")
    return start_date, mode


def fetch_rows(client, channel_id, video_ids, start_date, end_date):
    """Fetch complete video-day data without using fragile API pagination.

    If a request fills the response page (potential truncation), bisect the
    date range and fetch both halves. Retryable server failures also trigger
    date bisection, but non-server errors are raised immediately.
    """
    seen = set()
    records = []
    pages = 0
    headers = None

    def split_dates(batch, window_start, window_end):
        if window_start == window_end:
            raise RuntimeError(
                f"Cannot safely split the single-day Analytics window "
                f"{window_start}; refusing to write incomplete data"
            )
        middle = window_start + timedelta(days=(window_end - window_start).days // 2)
        fetch_window(batch, window_start, middle)
        fetch_window(batch, middle + timedelta(days=1), window_end)

    def fetch_window(batch, window_start, window_end):
        nonlocal pages, headers

        try:
            response = client.reports().query(
                ids=f"channel=={channel_id}",
                startDate=window_start.isoformat(),
                endDate=window_end.isoformat(),
                metrics=METRICS,
                dimensions="day,video",
                filters="video==" + ",".join(batch),
                sort="day,video",
                maxResults=PAGE_SIZE,
                # Deliberately do not use startIndex > 1: the API can 500.
            ).execute(num_retries=3)
            pages += 1
        except HttpError as error:
            # A large query can trigger a Google-side 5xx. Try smaller windows.
            if error.resp.status in (500, 502, 503, 504) and window_start < window_end:
                print(f"Server error for {window_start} to {window_end}; splitting window")
                split_dates(batch, window_start, window_end)
                return
            raise

        current_headers = response.get("columnHeaders", [])
        columns = [header["name"] for header in current_headers]
        if not {"day", "video", "views"}.issubset(columns):
            raise ValueError("Unexpected Analytics API columns")
        if headers is None:
            headers = current_headers
        elif headers != current_headers:
            raise ValueError("Inconsistent Analytics API columns")

        rows = response.get("rows", [])
        if len(rows) >= PAGE_SIZE:
            # A full page might hide further records. Do not silently truncate.
            print(f"Full page for {window_start} to {window_end}; splitting window")
            split_dates(batch, window_start, window_end)
            return

        for raw in rows:
            if len(raw) != len(columns):
                raise ValueError("Row and column lengths do not match")
            row = dict(zip(columns, raw))
            key = (row["day"], row["video"])
            if (
                row["video"] not in batch
                or not window_start <= date.fromisoformat(row["day"]) <= window_end
                or key in seen
                or not isinstance(row["views"], (int, float))
                or isinstance(row["views"], bool)
                or row["views"] < 0
            ):
                raise ValueError(f"Unexpected/duplicate analytics record: {key}")
            seen.add(key)
            records.append({
                "reporting_date": row["day"],
                "video_id": row["video"],
                "metrics": {k: v for k, v in row.items() if k not in ("day", "video")},
                "raw_row": raw,
            })

    for offset in range(0, len(video_ids), BATCH_SIZE):
        batch = video_ids[offset:offset + BATCH_SIZE]
        print(f"Video batch {offset // BATCH_SIZE + 1} "
              f"of {(len(video_ids) + BATCH_SIZE - 1) // BATCH_SIZE}")
        fetch_window(batch, start_date, end_date)

    return records, headers or [], pages


def main():
    channel, video_ids, video_manifest = load_videos()
    channel_id = channel["id"]
    end_date = datetime.now(timezone.utc).date() - timedelta(days=5)
    start_date, mode = select_window(channel_id, end_date)
    print("Channel:", channel.get("snippet", {}).get("title", "Unknown"))
    print("Channel ID:", channel_id)
    print("Video IDs:", len(video_ids))
    print("Mode:", mode, "| Window:", start_date, "to", end_date)

    client = build("youtubeAnalytics", "v2", credentials=authenticate(), cache_discovery=False)
    records, headers, pages = fetch_rows(client, channel_id, video_ids, start_date, end_date)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid4().hex[:8]
    extracted_at = datetime.now(timezone.utc).isoformat()
    folder = ANALYTICS_LANDING / run_id
    folder.mkdir(parents=True, exist_ok=False)
    with (folder / "video_daily.jsonl").open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps({
                "extract_run_id": run_id,
                "ingested_at_utc": extracted_at,
                "source_endpoint": "youtubeAnalytics.reports.query",
                "channel_id": channel_id,
                **record,
            }, ensure_ascii=False) + "\n")

    manifest = {
        "extract_run_id": run_id,
        "extracted_at_utc": extracted_at,
        "channel_id": channel_id,
        "mode": mode,
        "report_start_date": start_date.isoformat(),
        "report_end_date": end_date.isoformat(),
        "report_timezone": "America/Los_Angeles",
        "video_ids_requested": len(video_ids),
        "day2_missing_video_ids": video_manifest.get("missing_video_ids", []),
        "api_pages": pages,
        "record_count": len(records),
        "column_headers": headers,
        "max_reported_date": max((row["reporting_date"] for row in records), default=None),
        "status": "completed",
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
    temp = CHECKPOINT.with_suffix(".tmp")
    temp.write_text(json.dumps({
        "channel_id": channel_id,
        "last_successful_requested_end_date": end_date.isoformat(),
        "last_run_id": run_id,
    }, indent=2), encoding="utf-8")
    os.replace(temp, CHECKPOINT)

    print("Completed! Rows:", len(records), "| API pages:", pages)
    print("Landing:", folder)
    print("Checkpoint:", CHECKPOINT)
    if manifest["day2_missing_video_ids"]:
        print("Note: Day 2 has missing video details; coverage is not yet complete.")


if __name__ == "__main__":
    main()
