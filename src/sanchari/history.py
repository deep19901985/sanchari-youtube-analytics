"""Pure date-window helpers for historical YouTube Analytics backfills."""
from datetime import date, timedelta


def chunk_date_ranges(start: date, end: date, days: int = 90):
    """Yield contiguous, inclusive, non-overlapping (start, end) date windows."""
    if not isinstance(start, date) or not isinstance(end, date):
        raise TypeError("start and end must be dates")
    if days < 1:
        raise ValueError("days must be positive")
    if start > end:
        raise ValueError("start must be on or before end")
    cursor = start
    while cursor <= end:
        finish = min(cursor + timedelta(days=days - 1), end)
        yield cursor, finish
        cursor = finish + timedelta(days=1)
