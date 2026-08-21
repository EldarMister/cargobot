import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl


class WebAuthError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class TelegramWebUser:
    telegram_id: int
    first_name: str = ""
    username: str = ""


def validate_telegram_init_data(
    init_data: str,
    bot_token: str,
    *,
    max_age_seconds: int = 15 * 60,
    now: int | None = None,
) -> TelegramWebUser:
    if not init_data or not bot_token:
        raise WebAuthError("Missing Telegram authorization data")
    values = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = values.pop("hash", "")
    if not received_hash:
        raise WebAuthError("Missing Telegram signature")
    data_check_string = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(received_hash, calculated_hash):
        raise WebAuthError("Invalid Telegram signature")
    try:
        auth_date = int(values["auth_date"])
    except (KeyError, ValueError) as exc:
        raise WebAuthError("Invalid authorization date") from exc
    current_time = int(time.time()) if now is None else now
    if auth_date > current_time + 60 or current_time - auth_date > max_age_seconds:
        raise WebAuthError("Telegram authorization data expired")
    try:
        user_data = json.loads(values["user"])
        telegram_id = int(user_data["id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise WebAuthError("Invalid Telegram user data") from exc
    return TelegramWebUser(
        telegram_id=telegram_id,
        first_name=str(user_data.get("first_name", "")),
        username=str(user_data.get("username", "")),
    )


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_admin_session(
    telegram_id: int,
    bot_token: str,
    *,
    ttl_seconds: int = 12 * 60 * 60,
    now: int | None = None,
) -> str:
    current_time = int(time.time()) if now is None else now
    payload = json.dumps(
        {"telegram_id": telegram_id, "expires_at": current_time + ttl_seconds},
        separators=(",", ":"),
    ).encode()
    signature = hmac.new(bot_token.encode(), payload, hashlib.sha256).digest()
    return f"{_encode(payload)}.{_encode(signature)}"


def validate_admin_session(
    token: str,
    bot_token: str,
    *,
    now: int | None = None,
) -> int:
    try:
        encoded_payload, encoded_signature = token.split(".", 1)
        payload = _decode(encoded_payload)
        signature = _decode(encoded_signature)
    except (ValueError, TypeError) as exc:
        raise WebAuthError("Invalid admin session") from exc
    expected = hmac.new(bot_token.encode(), payload, hashlib.sha256).digest()
    if not hmac.compare_digest(signature, expected):
        raise WebAuthError("Invalid admin session")
    try:
        data = json.loads(payload)
        telegram_id = int(data["telegram_id"])
        expires_at = int(data["expires_at"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise WebAuthError("Invalid admin session") from exc
    current_time = int(time.time()) if now is None else now
    if expires_at < current_time:
        raise WebAuthError("Admin session expired")
    return telegram_id
