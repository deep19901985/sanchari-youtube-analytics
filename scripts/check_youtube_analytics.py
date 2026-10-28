
from datetime import datetime, timedelta, timezone

from googleapiclient.discovery import build

from check_youtube_connection import authenticate


def main():
    # Reuse the OAuth authentication from Day 2.
    credentials = authenticate()

    analytics = build(
        "youtubeAnalytics",
        "v2",
        credentials=credentials,
        cache_discovery=False,
    )

    # Leave a buffer for reporting delays.
    end_date = datetime.now(timezone.utc).date() - timedelta(days=5)
    start_date = end_date - timedelta(days=29)

    print("Checking Sanchari YouTube Analytics...")
    print("From:", start_date)
    print("To:", end_date)

    response = analytics.reports().query(
        ids="channel==MINE",
        startDate=start_date.isoformat(),
        endDate=end_date.isoformat(),
        metrics=(
            "views,estimatedMinutesWatched,"
            "averageViewDuration,likes,comments,shares"
        ),
        dimensions="day",
        sort="day",
        maxResults=200,
    ).execute(num_retries=3)

    columns = [
        item["name"]
        for item in response.get("columnHeaders", [])
    ]

    rows = response.get("rows", [])

    print("\nConnection successful!")
    print("Columns:", columns)
    print("Rows retrieved:", len(rows))

    for row in rows[:5]:
        print(dict(zip(columns, row)))

    if not rows:
        print("No analytics rows available for this period.")


if __name__ == "__main__":
    main()
