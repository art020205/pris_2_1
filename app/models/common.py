from datetime import date, datetime, time
from typing import Any

from bson import ObjectId


def now_utc() -> datetime:
    return datetime.utcnow()


def date_to_datetime(value: date | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.combine(value, time.min)


def oid(value: str | ObjectId) -> ObjectId:
    if isinstance(value, ObjectId):
        return value
    if not ObjectId.is_valid(value):
        raise ValueError("Invalid ObjectId")
    return ObjectId(value)


def serialize_doc(document: dict[str, Any] | None) -> dict[str, Any] | None:
    if document is None:
        return None
    result: dict[str, Any] = {}
    for key, value in document.items():
        output_key = "id" if key == "_id" else key
        if key == "birth_date" and isinstance(value, datetime):
            result[output_key] = value.date().isoformat()
        else:
            result[output_key] = serialize_value(value)
    return result


def serialize_value(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, list):
        return [serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: serialize_value(item) for key, item in value.items()}
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value
