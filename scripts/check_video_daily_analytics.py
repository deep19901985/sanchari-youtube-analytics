
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from googleapiclient.discovery import build
from check_youtube_connection import authenticate


PROJECT_ROOT = Path(__file__).resolve().parents[1]

LANDING_DIR = (
    PROJECT_ROOT / "data" / "landing" / "youtube_data_api"
)


def get_sample_video_id():
    """Read a video ID from the most recent Day 2 extraction."""
    files = sorted(
        LANDING_DIR.glob("*/videos.jsonl"),
        reverse=True,
    )

    for path in files:
        with path.open("r", encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue

                record = json.loads(line)
                video_id = record.get("video_id")

                if video_id:
                    return video_id

    raise RuntimeError(
        "No video IDs found. Check Day 2 landing data."
    )


def main():
    video_id = get_sample_video_id()
    print("Selected video:", video_id)

    analytics = build(
        "youtubeAnalytics",
        "v2",
        credentials=authenticate(),
        cache_discovery=False,
    )

    end_date = (
        datetime.now(timezone.utc).date()
        - timedelta(days=5)
    )
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

    columns = [
        column["name"]
        for column in response.get("columnHeaders", [])
    ]
    rows = response.get("rows", [])

    print("Date range:", start_date, "to", end_date)
    print("Rows retrieved:", len(rows))

    for row in rows[:10]:
        print(dict(zip(columns, row)))

    if not rows:
        print("No activity reported for this video in the period.")


if __name__ == "__main__":
    main()
