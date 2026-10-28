
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from googleapiclient.discovery import build

from check_youtube_connection import authenticate
from check_video_daily_analytics import get_sample_video_id


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main():
    video_id = get_sample_video_id()

    credentials = authenticate()
    analytics = build(
        "youtubeAnalytics",
        "v2",
        credentials=credentials,
        cache_discovery=False,
    )

    # Initial 90-day historical backfill
    end_date = datetime.now(timezone.utc).date() - timedelta(days=5)
    start_date = end_date - timedelta(days=89)

    response = analytics.reports().query(
        ids="channel==MINE",
        startDate=start_date.isoformat(),
        endDate=end_date.isoformat(),
        metrics=(
            "views,estimatedMinutesWatched,"
            "averageViewDuration,likes,comments,shares"
        ),
        dimensions="day,video",
        filters=f"video=={video_id}",
        sort="day",
        maxResults=200,
    ).execute(num_retries=3)

    headers = response.get("columnHeaders", [])
    columns = [header["name"] for header in headers]
    rows = response.get("rows", [])

    if not {"day", "video"}.issubset(columns):
        raise RuntimeError("Missing required report dimensions")

    # Every run has a unique immutable landing folder
    run_id = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "_" + uuid4().hex[:8]
    )

    output_dir = (
        PROJECT_ROOT / "data" / "landing"
        / "youtube_analytics_api" / run_id
    )
    output_dir.mkdir(parents=True, exist_ok=False)

    extracted_at = datetime.now(timezone.utc).isoformat()

    # Write one JSON record per daily observation
    output_file = output_dir / "video_daily.jsonl"

    with output_file.open("w", encoding="utf-8") as file:
        for row in rows:
            values = dict(zip(columns, row))

            record = {
                "extract_run_id": run_id,
                "ingested_at_utc": extracted_at,
                "source_endpoint": "youtubeAnalytics.reports.query",
                "reporting_date": values["day"],
                "video_id": values["video"],
                "metrics": {
                    key: value
                    for key, value in values.items()
                    if key not in ("day", "video")
                },
                "raw_row": row,
            }

            file.write(
                json.dumps(record, ensure_ascii=False) + "\n"
            )

    # Metadata for traceability and future replay
    manifest = {
        "extract_run_id": run_id,
        "extracted_at_utc": extracted_at,
        "requested_video_id": video_id,
        "report_start_date": start_date.isoformat(),
        "report_end_date": end_date.isoformat(),
        "report_timezone": "America/Los_Angeles",
        "column_headers": headers,
        "record_count": len(rows),
        "status": "completed",
    }

    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    print("\nHistorical extraction completed!")
    print("Video:", video_id)
    print("Records saved:", len(rows))
    print("Output:", output_dir)

    if not rows:
        print("Warning: no data returned for this video.")


if __name__ == "__main__":
    main()
