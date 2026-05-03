import json
from datetime import date
from typing import Any, Dict, List

from shared.auth import AuthError, resolve_ui_hub_id, validate_ui_auth
from shared.compiler import CompilerValidationError, compile_schedule
from shared.dynamodb import get_action_catalogs_table, get_schedules_table
from shared.responses import cors_debug_info, error_response, json_response


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
    delete_keys = []
    for item in existing_items:
        item_key = item.get("itemKey", "")
        if any(item_key.startswith(prefix) for prefix in ("DEF#", "DAY#", "EVT#", "BROKEN#")):
            delete_keys.append({"hubId": hub_id, "itemKey": item_key})

    new_items = [
        compile_result["metaItem"],
        *compile_result["definitionItems"],
        *compile_result["dayItems"],
        *compile_result["eventItems"],
        *compile_result["brokenItems"],
    ]

    if hasattr(schedules_table, "batch_writer"):
        with schedules_table.batch_writer() as batch:
            for key in delete_keys:
                batch.delete_item(Key=key)
            for item in new_items:
                batch.put_item(Item=item)
        return

    for key in delete_keys:
        schedules_table.delete_item(Key=key)
    for item in new_items:
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
    except CompilerValidationError as exc:
        return json_response(400, exc.as_error(), event=event)
    except Exception:
        return error_response(500, "INTERNAL_ERROR", "Unexpected server error", event=event)
