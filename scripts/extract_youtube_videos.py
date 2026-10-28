
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from sanchari.youtube_ingestion import fetch_uploaded_video_ids

from googleapiclient.discovery import build
from check_youtube_connection import authenticate

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def main():
    # 1. Reuse existing OAuth credentials
    youtube = build(
        "youtube", "v3",
        credentials=authenticate(),
        cache_discovery=False,
    )

    # 2. Find the channel's uploads playlist
    response = youtube.channels().list(
        part="snippet,statistics,contentDetails",
        mine=True,
    ).execute(num_retries=3)

    channels = response.get("items", [])
    if not channels:
        raise RuntimeError("No authorised YouTube channel found")

    channel = channels[0]
    playlist_id = channel["contentDetails"]["relatedPlaylists"]["uploads"]

    print("Channel:", channel["snippet"]["title"])

    # 3. Retrieve uploaded video IDs using pagination
    video_ids = []
    page_token = None
    page_number = 0

    while True:
        params = {
            "part": "contentDetails",
            "playlistId": playlist_id,
            "maxResults": 50,
        }

        if page_token:
            params["pageToken"] = page_token

        page = youtube.playlistItems().list(
            **params
        ).execute(num_retries=3)

        page_number += 1

        for item in page.get("items", []):
            video_id = item.get("contentDetails", {}).get("videoId")
            if video_id:
                video_ids.append(video_id)

        print(f"Retrieved playlist page {page_number}")

        page_token = page.get("nextPageToken")
        if not page_token:
            break

    # Preserve order while removing duplicate IDs
    # video_ids = list(dict.fromkeys(video_ids))
    # 3. Retrieve uploaded video IDs using reusable pagination
    video_ids = fetch_uploaded_video_ids(youtube, playlist_id)
    print("Unique uploaded video IDs:", len(video_ids))

    if not video_ids:
        raise RuntimeError("No uploaded video IDs returned")

    # 4. Create a separate immutable landing folder per run
    run_id = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "_" + uuid4().hex[:8]
    )

    output_dir = (
        PROJECT_ROOT / "data" / "landing"
        / "youtube_data_api" / run_id
    )
    output_dir.mkdir(parents=True, exist_ok=False)

    (output_dir / "channel.json").write_text(
        json.dumps(channel, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # 5. Fetch video details in batches of 50
    returned_ids = set()
    output_file = output_dir / "videos.jsonl"

    with output_file.open("w", encoding="utf-8") as file:
        for start in range(0, len(video_ids), 50):
            batch = video_ids[start:start + 50]

            details = youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=",".join(batch),
            ).execute(num_retries=3)

            for video in details.get("items", []):
                returned_ids.add(video["id"])

                record = {
                    "extract_run_id": run_id,
                    "ingested_at_utc": utc_now(),
                    "source_endpoint": "youtube.videos.list",
                    "channel_id": channel["id"],
                    "video_id": video["id"],
                    "payload": video,
                }

                file.write(
                    json.dumps(record, ensure_ascii=False) + "\n"
                )

            print(
                f"Processed batch {start // 50 + 1}: "
                f"{len(returned_ids)} videos"
            )

    # 6. Write extraction metadata for audit/replay
    missing_ids = [
        video_id for video_id in video_ids
        if video_id not in returned_ids
    ]

    manifest = {
        "extract_run_id": run_id,
        "extracted_at_utc": utc_now(),
        "channel_id": channel["id"],
        "playlist_video_ids": len(video_ids),
        "video_records": len(returned_ids),
        "missing_video_ids": missing_ids,
        "status": "completed",
    }

    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    print("\nExtraction completed!")
    print("Videos saved:", len(returned_ids))
    print("IDs without details:", len(missing_ids))
    print("Output directory:", output_dir)


if __name__ == "__main__":
    main()
