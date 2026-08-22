import re
from datetime import date, datetime
from decimal import Decimal

CLIENT_CODE_RE = re.compile(r"^H-(\d+)$", re.IGNORECASE)
TRACKING_RE = re.compile(r"^[A-Z0-9][A-Z0-9._/-]{5,127}$", re.IGNORECASE)
DATE_TEXT_RE = re.compile(r"(?:\d{4}[年./-]\d{1,2}[月./-]\d{1,2}日?|^AD\s*\d{4})", re.IGNORECASE)


def normalize_client_code(value: object) -> str:
    text = str(value or "").strip().upper()
    text = re.sub(r"\s+", "", text)
    return text


def is_valid_client_code(value: object) -> bool:
    match = CLIENT_CODE_RE.fullmatch(normalize_client_code(value))
    return bool(match and int(match.group(1)) >= 801)


def normalize_tracking_number(value: object) -> str:
    if value is None or isinstance(value, (date, datetime)):
        return ""
    if isinstance(value, bool):
        return ""
    if isinstance(value, int):
        return str(value)
    if isinstance(value, (float, Decimal)):
        decimal_value = Decimal(str(value))
        if decimal_value == decimal_value.to_integral_value():
            return format(decimal_value.quantize(Decimal(1)), "f")
        return format(decimal_value.normalize(), "f")
    return re.sub(r"\s+", "", str(value).strip()).upper()


def is_valid_tracking_number(value: object) -> bool:
    tracking = normalize_tracking_number(value)
    if not tracking or is_valid_client_code(tracking) or DATE_TEXT_RE.search(tracking):
        return False
    if tracking.lower() in {"tracking", "trackingnumber", "трек", "трек-код", "треккод"}:
        return False
    return bool(TRACKING_RE.fullmatch(tracking)) and any(char.isdigit() for char in tracking)


def normalize_name(value: str) -> str:
    return " ".join(value.casefold().split())


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    return f"+{digits}" if digits else ""
