from datetime import date
import pytest
from sanchari.history import chunk_date_ranges


def test_quarter_2023_is_one_90_day_window():
    assert list(chunk_date_ranges(date(2023, 1, 1), date(2023, 3, 31))) == [
        (date(2023, 1, 1), date(2023, 3, 31))
    ]


def test_windows_non_overlapping_and_cover_exact_range():
    windows = list(chunk_date_ranges(date(2023, 1, 1), date(2024, 1, 15), 90))
    assert windows[0][0] == date(2023, 1, 1)
    assert windows[-1][1] == date(2024, 1, 15)
    from datetime import timedelta
    assert all(a[1] + timedelta(days=1) == b[0] for a, b in zip(windows, windows[1:]))
    assert all((end - start).days <= 89 for start, end in windows)


def test_leap_day_included():
    windows = list(chunk_date_ranges(date(2024, 2, 28), date(2024, 3, 1), 2))
    assert windows == [(date(2024, 2, 28), date(2024, 2, 29)),
                       (date(2024, 3, 1), date(2024, 3, 1))]


@pytest.mark.parametrize("days", [0, -5])
def test_invalid_chunk_sizes(days):
    with pytest.raises(ValueError):
        list(chunk_date_ranges(date(2023, 1, 1), date(2023, 1, 5), days))


def test_invalid_date_order():
    with pytest.raises(ValueError):
        list(chunk_date_ranges(date(2025, 1, 2), date(2025, 1, 1)))
