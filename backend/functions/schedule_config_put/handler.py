import json
from datetime import date
from typing import Any, Dict, List

from shared.auth import AuthError, resolve_ui_hub_id, validate_ui_auth
from shared.compiler import CompilerValidationError, compile_schedule
from shared.dynamodb import get_action_catalogs_table, get_schedules_table
from shared.responses import error_response, json_response


def _parse_json_body(event: Dict[str, Any]) -> Dict[str, Any]:
    body = event.get("body")
    if body is None:
        raise CompilerValidationError("Request body is required")

    if isinstance(body, str):
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise CompilerValidationError("Invalid JSON body") from exc
    elif isinstance(body, dict):
        parsed = body
    else:
        raise CompilerValidationError("Request body must be JSON")

    if not isinstance(parsed, dict):
        raise CompilerValidationError("Request body must be a JSON object")
    return parsed


def _require_fields(payload: Dict[str, Any], fields: List[str]) -> None:
    missing = [field for field in fields if field not in payload]
    if missing:
        raise CompilerValidationError(f"Missing required field(s): {', '.join(missing)}")


def _load_current_version(schedules_table: Any, hub_id: str) -> int:
    meta_item = schedules_table.get_item(Key={"hubId": hub_id, "itemKey": "META"}).get("Item")
    if not meta_item:
        return 0
    return int(meta_item.get("scheduleVersion", 0))


def _load_current_items(schedules_table: Any, hub_id: str) -> List[Dict[str, Any]]:
    try:
        from boto3.dynamodb.conditions import Key

        response = schedules_table.query(KeyConditionExpression=Key("hubId").eq(hub_id))
    except ModuleNotFoundError:
        response = schedules_table.query()
    return response.get("Items", [])


def _replace_items(schedules_table: Any, hub_id: str, compile_result: Dict[str, Any]) -> None:
    existing_items = _load_current_items(schedules_table, hub_id)
    for item in existing_items:
        item_key = item.get("itemKey", "")
        if item_key.startswith("DEF#") or item_key.startswith("DAY#"):
            schedules_table.delete_item(Key={"hubId": hub_id, "itemKey": item_key})
        if item_key.startswith("EVT#") or item_key.startswith("BROKEN#"):
            schedules_table.delete_item(Key={"hubId": hub_id, "itemKey": item_key})

    schedules_table.put_item(Item=compile_result["metaItem"])
    for item in compile_result["definitionItems"]:
        schedules_table.put_item(Item=item)
    for item in compile_result["dayItems"]:
        schedules_table.put_item(Item=item)
    for item in compile_result["eventItems"]:
        schedules_table.put_item(Item=item)
    for item in compile_result["brokenItems"]:
        schedules_table.put_item(Item=item)


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    try:
        claims = validate_ui_auth(event)
        payload = _parse_json_body(event)

        _require_fields(payload, ["meta", "scheduleDefinitions", "dayConfigs"])
        hub_id = payload.get("hubId") or resolve_ui_hub_id(event, claims)

        catalog_table = get_action_catalogs_table()
        catalog_item = catalog_table.get_item(Key={"hubId": hub_id}).get("Item")
        if not catalog_item:
            raise CompilerValidationError("No action catalog present for hub")

        schedules_table = get_schedules_table()
        current_version = _load_current_version(schedules_table, hub_id)
        next_version = current_version + 1

        compile_result = compile_schedule(
            hub_id=hub_id,
            schedule_definitions=payload["scheduleDefinitions"],
            day_configs=payload["dayConfigs"],
            catalog=catalog_item,
            schedule_version=next_version,
            timezone="America/New_York",
            start_date=date.today(),
            days=7,
        )

        _replace_items(schedules_table, hub_id, compile_result)

        return json_response(
            200,
            {
                "hubId": hub_id,
                "status": "ok",
                "scheduleVersion": compile_result["metaItem"]["scheduleVersion"],
                "compiledAt": compile_result["metaItem"]["compiledAt"],
                "compiledPreview": compile_result["compiledPreview"],
                "brokenReferences": compile_result["brokenReferences"],
            },
        )
    except AuthError as exc:
        return error_response(401, "UNAUTHORIZED", str(exc))
    except CompilerValidationError as exc:
        return json_response(400, exc.as_error())
    except Exception:
        return error_response(500, "INTERNAL_ERROR", "Unexpected server error")
