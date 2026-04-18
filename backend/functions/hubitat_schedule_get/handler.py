from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

from shared.auth import AuthError, validate_hubitat_token
from shared.dynamodb import get_schedules_table
from shared.responses import error_response, json_response


def _parse_days(value: str | None) -> int:
    if value is None:
        return 7
    try:
        days = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("days must be an integer") from exc

    if days < 1 or days > 90:
        raise ValueError("days must be between 1 and 90")
    return days


def _load_items(table: Any, hub_id: str) -> List[Dict[str, Any]]:
    try:
        from boto3.dynamodb.conditions import Key

        response = table.query(KeyConditionExpression=Key("hubId").eq(hub_id))
    except ModuleNotFoundError:
        response = table.query()
    return response.get("Items", [])


def _today_in_timezone(timezone_name: str) -> datetime:
    return datetime.now(ZoneInfo(timezone_name))


def _in_window(item_date: str, start_date: datetime, days: int) -> bool:
    start = start_date.date()
    end = (start_date + timedelta(days=days - 1)).date()
    current = datetime.strptime(item_date, "%Y-%m-%d").date()
    return start <= current <= end


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    try:
        validate_hubitat_token(event)
        query = event.get("queryStringParameters") or {}

        hub_id = query.get("hubId")
        if not hub_id:
            return error_response(400, "VALIDATION_ERROR", "hubId is required")

        days = _parse_days(query.get("days"))

        table = get_schedules_table()
        items = _load_items(table, hub_id)

        meta_item = next((item for item in items if item.get("itemKey") == "META"), None)
        schedule_version = (meta_item or {}).get("scheduleVersion", 0)
        timezone_name = (meta_item or {}).get("timezone", "America/New_York")

        today = _today_in_timezone(timezone_name)
        events = []

        for item in items:
            key = item.get("itemKey", "")
            if key.startswith("EVT#"):
                if _in_window(item.get("date", ""), today, days):
                    events.append(
                        {
                            "eventId": item.get("eventId"),
                            "date": item.get("date"),
                            "time": item.get("time"),
                            "actionType": item.get("actionType"),
                            "parameters": item.get("parameters", {}),
                            "sourceScheduleId": item.get("sourceScheduleId"),
                        }
                    )
            elif key.startswith("BROKEN#"):
                if _in_window(item.get("date", ""), today, days):
                    events.append(
                        {
                            "eventId": item.get("eventId"),
                            "date": item.get("date"),
                            "time": item.get("time", "00:00"),
                            "sourceScheduleId": item.get("sourceScheduleId"),
                            "validation": {
                                "status": "broken",
                                "message": item.get("message", "Unknown error"),
                                "originalLabel": item.get("originalLabel", ""),
                            },
                        }
                    )

        events.sort(key=lambda x: (x.get("date", ""), x.get("time", ""), x.get("eventId", "")))

        return json_response(
            200,
            {
                "hubId": hub_id,
                "generatedAt": datetime.now(UTC).replace(microsecond=0).isoformat().replace(
                    "+00:00", "Z"
                ),
                "scheduleVersion": schedule_version,
                "timezone": timezone_name,
                "events": events,
            },
        )
    except AuthError:
        return error_response(401, "UNAUTHORIZED", "Invalid Hubitat token")
    except ValueError as exc:
        return error_response(400, "VALIDATION_ERROR", str(exc))
    except Exception:
        return error_response(500, "INTERNAL_ERROR", "Unexpected server error")
