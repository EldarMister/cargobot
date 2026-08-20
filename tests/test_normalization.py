import pytest

from app.services.normalization import (
    is_valid_client_code,
    normalize_client_code,
    normalize_tracking_number,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("j-8226", "J-8226"), (" J-0001 ", "J-0001"), ("j - 329", "J-329")],
)
def test_normalize_client_code(raw, expected):
    assert normalize_client_code(raw) == expected


@pytest.mark.parametrize("code", ["J-1", "J-0001", "j-8226", " j - 55 "])
def test_valid_client_code(code):
    assert is_valid_client_code(code)


@pytest.mark.parametrize("code", ["", "8226", "K-12", "J-", "J-ABC", "J-1-2"])
def test_invalid_client_code(code):
    assert not is_valid_client_code(code)


def test_numeric_tracking_does_not_use_scientific_notation():
    assert normalize_tracking_number(9812328869266.0) == "9812328869266"
