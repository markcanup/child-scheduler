import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from shared.auth import AuthError, resolve_ui_hub_id, validate_ui_auth
from shared.dynamodb import get_schedules_table
from shared.responses import cors_debug_info, error_response, json_response


def _query_schedule_items(table: Any, hub_id: str) -> List[Dict[str, Any]]:
    from boto3.dynamodb.conditions import Key

    response = table.query(KeyConditionExpression=Key("hubId").eq(hub_id))
    return response.get("Items", [])


def _default_meta() -> Dict[str, Any]:
    return {
        "scheduleVersion": 0,
        "compiledAt": None,
        "timezone": "America/New_York",
    }


def _group_schedule_items(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    meta = _default_meta()
    schedule_definitions = []
    day_configs = []
    compiled_preview = []
    broken_references = []

    for item in items:
        item_key = item.get("itemKey", "")

        if item_key == "META":
            meta = {
                "scheduleVersion": item.get("scheduleVersion", 0),
                "compiledAt": item.get("compiledAt"),
                "timezone": item.get("timezone", "America/New_York"),
            }
        elif item_key.startswith("DEF#"):
            schedule_definitions.append(item)
        elif item_key.startswith("DAY#"):
            day_configs.append(item)
        elif item_key.startswith("EVT#"):
            compiled_preview.append(item)
        elif item_key.startswith("BROKEN#"):
            broken_references.append(item)

    schedule_definitions.sort(key=lambda x: x.get("itemKey", ""))
    day_configs.sort(key=lambda x: x.get("itemKey", ""))
    compiled_preview.sort(key=lambda x: x.get("itemKey", ""))
    broken_references.sort(key=lambda x: x.get("itemKey", ""))

    return {
        "meta": _normalize_for_json(meta),
        "scheduleDefinitions": _normalize_for_json(schedule_definitions),
        "dayConfigs": _normalize_for_json(day_configs),
        "compiledPreview": _normalize_for_json(compiled_preview),
        "brokenReferences": _normalize_for_json(broken_references),
    }


def _normalize_number(value: Decimal) -> int | float:
    if value % 1 == 0:
        return int(value)
    return float(value)


def _normalize_for_json(value: Any) -> Any:
    if isinstance(value, Decimal):
        return _normalize_number(value)
    if isinstance(value, list):
        return [_normalize_for_json(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalize_for_json(item) for key, item in value.items()}
    return value


def _normalize_rotation_timestamp(raw_value: str) -> Optional[str]:
    raw = (raw_value or "").strip()
    if not raw:
        return None

    # Preferred operational format from deployment metadata:
    # YYYY-MM-DD.HH:MM:SS (treated as UTC).
    try:
        parsed = datetime.strptime(raw, "%Y-%m-%d.%H:%M:%S").replace(tzinfo=timezone.utc)
        return parsed.isoformat().replace("+00:00", "Z")
    except ValueError:
        pass

    # Also allow ISO-8601 if already provided.
    try:
        normalized_iso = raw.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized_iso)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        else:
            parsed = parsed.astimezone(timezone.utc)
        return parsed.isoformat().replace("+00:00", "Z")
    except ValueError:
        return None


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    try:
        claims = validate_ui_auth(event)
        hub_id = resolve_ui_hub_id(event, claims)

        table = get_schedules_table()
        items = _query_schedule_items(table, hub_id)
        grouped = _group_schedule_items(items)

        return json_response(
            200,
            {
                "hubId": hub_id,
                **grouped,
                "security": {
                    "hubitatTokenLastRotatedAt": _normalize_rotation_timestamp(
                        os.environ.get("HUBITAT_TOKEN_LAST_ROTATED", "")
                    )
                },
            },
            event=event,
        )
    except AuthError as exc:
        return error_response(
            401,
            "UNAUTHORIZED",
            str(exc),
            event=event,
            details={
                "authMode": "cognito-jwt",
                "cors": cors_debug_info(event),
            },
        )
    except Exception:
        return error_response(500, "INTERNAL_ERROR", "Unexpected server error", event=event)
