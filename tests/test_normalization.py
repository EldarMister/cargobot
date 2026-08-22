import pytest

from app.services.normalization import (
    is_valid_client_code,
    normalize_client_code,
    normalize_tracking_number,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("h-8226", "H-8226"), (" H-801 ", "H-801"), ("h - 829", "H-829")],
)
def test_normalize_client_code(raw, expected):
    assert normalize_client_code(raw) == expected


@pytest.mark.parametrize("code", ["H-801", "H-802", "h-8226", " h - 999 "])
def test_valid_client_code(code):
    assert is_valid_client_code(code)


@pytest.mark.parametrize("code", ["", "8226", "J-801", "H-800", "H-", "H-ABC", "H-1-2"])
def test_invalid_client_code(code):
    assert not is_valid_client_code(code)


def test_numeric_tracking_does_not_use_scientific_notation():
    assert normalize_tracking_number(9812328869266.0) == "9812328869266"
