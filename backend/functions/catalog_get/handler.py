from decimal import Decimal
from typing import Any, Dict

from shared.auth import AuthError, resolve_ui_hub_id, validate_ui_auth
from shared.dynamodb import get_action_catalogs_table
from shared.responses import cors_debug_info, error_response, json_response


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


def _build_catalog_response(item: Dict[str, Any], resolved_hub_id: str) -> Dict[str, Any]:
    return {
        "hubId": item.get("hubId", resolved_hub_id),
        "generatedAt": item.get("generatedAt") or item.get("updatedAt") or "",
        "catalogVersion": _normalize_for_json(item.get("catalogVersion", "")),
        "actionDefinitions": _normalize_for_json(item.get("actionDefinitions") or []),
        "resources": _normalize_for_json(item.get("resources") or []),
    }


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    try:
        claims = validate_ui_auth(event)
        hub_id = resolve_ui_hub_id(event, claims)

        table = get_action_catalogs_table()
        result = table.get_item(Key={"hubId": hub_id})
        item = result.get("Item")

        if not item:
            return error_response(404, "NOT_FOUND", "Catalog not found", event=event)

        return json_response(200, _build_catalog_response(item, hub_id), event=event)
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
