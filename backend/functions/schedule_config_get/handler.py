from typing import Any, Dict, List

from shared.auth import AuthError, resolve_ui_hub_id, validate_ui_auth
from shared.dynamodb import get_schedules_table
from shared.responses import error_response, json_response


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
        "meta": meta,
        "scheduleDefinitions": schedule_definitions,
        "dayConfigs": day_configs,
        "compiledPreview": compiled_preview,
        "brokenReferences": broken_references,
    }


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    try:
        validate_ui_auth(event)
        hub_id = resolve_ui_hub_id(event)

        table = get_schedules_table()
        items = _query_schedule_items(table, hub_id)
        grouped = _group_schedule_items(items)

        return json_response(
            200,
            {
                "hubId": hub_id,
                **grouped,
            },
        )
    except AuthError as exc:
        return error_response(401, "UNAUTHORIZED", str(exc))
    except Exception:
        return error_response(500, "INTERNAL_ERROR", "Unexpected server error")
