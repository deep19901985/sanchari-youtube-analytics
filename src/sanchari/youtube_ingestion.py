
"""Reusable YouTube ingestion helpers."""


def fetch_uploaded_video_ids(youtube, playlist_id):
    """Retrieve all video IDs from an uploads playlist."""
    video_ids = []
    page_token = None
    seen_tokens = set()

    while True:
        params = {
            "part": "contentDetails",
            "playlistId": playlist_id,
            "maxResults": 50,
        }

        if page_token:
            params["pageToken"] = page_token

        response = youtube.playlistItems().list(
            **params
        ).execute(num_retries=3)

        for item in response.get("items", []):
            video_id = item.get(
                "contentDetails", {}
            ).get("videoId")

            if video_id:
                video_ids.append(video_id)

        page_token = response.get("nextPageToken")

        if not page_token:
            break

        if page_token in seen_tokens:
            raise RuntimeError(
                "Repeated YouTube pagination token"
            )

        seen_tokens.add(page_token)

    return list(dict.fromkeys(video_ids))
