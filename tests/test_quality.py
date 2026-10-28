from sanchari.quality import require_fields, is_nonnegative_number


def test_required_fields_present():
    assert require_fields({"video_id": "abc123", "views": 5}, ("video_id", "views"))


def test_required_fields_reject_missing_values():
    assert not require_fields({"video_id": ""}, ("video_id",))
    assert not require_fields({"video_id": None}, ("video_id",))
    assert not require_fields({}, ("video_id",))


def test_nonnegative_numeric_values():
    assert is_nonnegative_number(0)
    assert is_nonnegative_number(12.5)
    assert not is_nonnegative_number(-1)
    assert not is_nonnegative_number(True)
    assert not is_nonnegative_number("12")
    assert not is_nonnegative_number(float('nan'))
