import json
from datetime import datetime, timezone
from typing import Any, Dict

from shared.auth import AuthError, validate_hubitat_token
from shared.catalog import (
    ValidationError,
    build_resource_index,
    validate_action_catalog_payload,
)
from shared.compiler import compile_schedule
from shared.dynamodb import get_action_catalogs_table
from shared.responses import error_response, json_response


def _parse_json_body(event: Dict[str, Any]) -> Dict[str, Any]:
    body = event.get("body")
    if body is None:
        raise ValidationError("Request body is required")

    if isinstance(body, str):
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ValidationError("Invalid JSON body") from exc
    elif isinstance(body, dict):
        parsed = body
    else:
        raise ValidationError("Request body must be JSON")

    if not isinstance(parsed, dict):
        raise ValidationError("Request body must be a JSON object")

    return parsed


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    try:
        validate_hubitat_token(event)
        payload = _parse_json_body(event)
        validate_action_catalog_payload(payload)

        resources = payload["resources"]
        received_at = datetime.now(timezone.utc).isoformat()
        item = {
            "hubId": payload["hubId"],
            "generatedAt": payload["generatedAt"],
            "catalogVersion": payload["catalogVersion"],
            "actionDefinitions": payload["actionDefinitions"],
            "resources": resources,
            "resourceIndex": build_resource_index(resources),
            "updatedAt": received_at,
        }

        table = get_action_catalogs_table()
        table.put_item(Item=item)

        compile_schedule(hub_id=payload["hubId"], reason="catalog_updated")

        return json_response(
            200,
            {
                "hubId": payload["hubId"],
                "status": "ok",
                "receivedAt": received_at,
                "resourceCount": len(resources),
            },
        )
    except AuthError:
        return error_response(401, "UNAUTHORIZED", "Invalid Hubitat token")
    except ValidationError as exc:
        return error_response(400, "VALIDATION_ERROR", str(exc))
    except Exception:
        return error_response(500, "INTERNAL_ERROR", "Unexpected server error")
