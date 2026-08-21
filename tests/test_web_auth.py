import hashlib
import hmac
import json
from urllib.parse import urlencode

import pytest

from app.web.auth import (
    WebAuthError,
    create_admin_session,
    validate_admin_session,
    validate_telegram_init_data,
)

BOT_TOKEN = "123456:test-token"


def telegram_init_data(telegram_id: int, auth_date: int) -> str:
    values = {
        "auth_date": str(auth_date),
        "query_id": "AAEAAAE",
        "user": json.dumps(
            {"id": telegram_id, "first_name": "Admin", "username": "bcl_admin"},
            separators=(",", ":"),
        ),
    }
    data_check_string = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    values["hash"] = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()
    return urlencode(values)


def test_valid_telegram_mini_app_data_identifies_admin():
    user = validate_telegram_init_data(
        telegram_init_data(777, 1_000),
        BOT_TOKEN,
        now=1_100,
    )

    assert user.telegram_id == 777
    assert user.first_name == "Admin"
    assert user.username == "bcl_admin"


def test_tampered_or_expired_telegram_data_is_rejected():
    valid = telegram_init_data(777, 1_000)

    with pytest.raises(WebAuthError, match="signature"):
        validate_telegram_init_data(valid.replace("777", "778"), BOT_TOKEN, now=1_100)

    with pytest.raises(WebAuthError, match="expired"):
        validate_telegram_init_data(valid, BOT_TOKEN, now=2_000)


def test_admin_session_is_signed_and_expires():
    token = create_admin_session(777, BOT_TOKEN, ttl_seconds=300, now=1_000)

    assert validate_admin_session(token, BOT_TOKEN, now=1_100) == 777

    with pytest.raises(WebAuthError, match="expired"):
        validate_admin_session(token, BOT_TOKEN, now=1_301)

    with pytest.raises(WebAuthError, match="Invalid"):
        validate_admin_session(f"{token}x", BOT_TOKEN, now=1_100)
