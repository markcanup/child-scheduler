from typing import Any, Dict

from shared.auth import AuthError, resolve_ui_hub_id, validate_ui_auth
from shared.dynamodb import get_action_catalogs_table
from shared.responses import error_response, json_response


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    try:
        claims = validate_ui_auth(event)
        hub_id = resolve_ui_hub_id(event, claims)

        table = get_action_catalogs_table()
        result = table.get_item(Key={"hubId": hub_id})
        item = result.get("Item")

        if not item:
            return error_response(404, "NOT_FOUND", "Catalog not found")

        return json_response(
            200,
            {
                "hubId": item["hubId"],
                "generatedAt": item["generatedAt"],
                "catalogVersion": item["catalogVersion"],
                "actionDefinitions": item.get("actionDefinitions", []),
                "resources": item.get("resources", []),
            },
        )
    except AuthError as exc:
        return error_response(401, "UNAUTHORIZED", str(exc))
    except Exception:
        return error_response(500, "INTERNAL_ERROR", "Unexpected server error")
