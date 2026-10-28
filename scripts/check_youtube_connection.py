
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Project configuration
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLIENT_FILE = PROJECT_ROOT / "client_secret_sanchari.json"
TOKEN_FILE = PROJECT_ROOT / "token_sanchari.json"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


def authenticate():
    """Authenticate securely with Google OAuth 2.0."""
    credentials = None

    if TOKEN_FILE.exists():
        credentials = Credentials.from_authorized_user_file(
            str(TOKEN_FILE), SCOPES
        )

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

    if not credentials or not credentials.valid:
        if not CLIENT_FILE.exists():
            raise FileNotFoundError(
                f"OAuth credentials not found: {CLIENT_FILE}"
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            str(CLIENT_FILE), SCOPES
        )
        credentials = flow.run_local_server(port=0)

    # Store locally for subsequent runs (never commit this file).
    TOKEN_FILE.write_text(credentials.to_json(), encoding="utf-8")

    return credentials


def main():
    credentials = authenticate()

    youtube = build("youtube", "v3", credentials=credentials)

    response = youtube.channels().list(
        part="snippet,statistics,contentDetails",
        mine=True,
    ).execute()

    channels = response.get("items", [])

    if not channels:
        raise RuntimeError(
            "No YouTube channel found for the authorised account."
        )

    for channel in channels:
        print("Connection successful!")
        print("Channel:", channel["snippet"]["title"])
        print("Channel ID:", channel["id"])

        stats = channel.get("statistics", {})
        print("Total views:", stats.get("viewCount", "Unavailable"))
        print("Video count:", stats.get("videoCount", "Unavailable"))
        print("Subscribers:", stats.get("subscriberCount", "Hidden"))


if __name__ == "__main__":
    main()
