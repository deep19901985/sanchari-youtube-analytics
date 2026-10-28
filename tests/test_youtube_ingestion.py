
from unittest.mock import Mock

import pytest

from sanchari.youtube_ingestion import fetch_uploaded_video_ids


def make_video(video_id):
    return {"contentDetails": {"videoId": video_id}}


def mock_youtube(*pages):
    youtube = Mock()
    youtube.playlistItems.return_value.list.return_value.execute.side_effect = list(pages)
    return youtube


def test_pagination():
    youtube = mock_youtube(
        {
            "items": [make_video("v1"), make_video("v2")],
            "nextPageToken": "page2",
        },
        {
            "items": [make_video("v3")],
        },
    )

    result = fetch_uploaded_video_ids(youtube, "uploads")

    assert result == ["v1", "v2", "v3"]
    assert youtube.playlistItems.return_value.list.call_count == 2


def test_duplicate_removal():
    youtube = mock_youtube(
        {
            "items": [
                make_video("v1"),
                make_video("v1"),
                make_video("v2"),
                {"contentDetails": {}},
            ]
        }
    )

    assert fetch_uploaded_video_ids(youtube, "uploads") == ["v1", "v2"]


def test_repeated_pagination_token():
    youtube = mock_youtube(
        {"items": [], "nextPageToken": "page2"},
        {"items": [], "nextPageToken": "page2"},
    )

    with pytest.raises(RuntimeError, match="Repeated"):
        fetch_uploaded_video_ids(youtube, "uploads")
