import json
import os
from typing import Any, Dict, List, Optional


def _split_csv(value: str) -> List[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _resolve_allowed_origins() -> List[str]:
    configured = os.environ.get("ALLOWED_ORIGINS", "")
    if configured:
        return _split_csv(configured)
    return []


def _event_header(event: Optional[Dict[str, Any]], name: str) -> Optional[str]:
    if not event:
        return None
    headers = event.get("headers") or {}
    return headers.get(name) or headers.get(name.lower())


def build_cors_headers(event: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    headers: Dict[str, str] = {
        "Content-Type": "application/json",
        "Vary": "Origin",
    }

    request_origin = _event_header(event, "Origin")
    allowed_origins = _resolve_allowed_origins()

    if request_origin and ("*" in allowed_origins or request_origin in allowed_origins):
        headers["Access-Control-Allow-Origin"] = request_origin if request_origin != "null" else "null"
        headers["Access-Control-Allow-Credentials"] = "true"
        headers["X-Cors-Origin-Matched"] = "true"
    elif request_origin:
        headers["X-Cors-Origin-Matched"] = "false"

    headers["X-Cors-Allowed-Origins"] = ",".join(allowed_origins) if allowed_origins else "<none-configured>"
    return headers


def cors_debug_info(event: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    request_origin = _event_header(event, "Origin")
    allowed_origins = _resolve_allowed_origins()
    return {
        "origin": request_origin,
        "allowedOrigins": allowed_origins,
        "originMatched": bool(
            request_origin and ("*" in allowed_origins or request_origin in allowed_origins)
        ),
        "path": (event or {}).get("rawPath"),
        "method": (event or {}).get("requestContext", {}).get("http", {}).get("method"),
    }


def json_response(status_code: int, body: Dict[str, Any], event: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": build_cors_headers(event),
        "body": json.dumps(body),
    }


def error_response(
    status_code: int,
    code: str,
    message: str,
    event: Optional[Dict[str, Any]] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    error: Dict[str, Any] = {
        "code": code,
        "message": message,
    }
    if details:
        error["details"] = details

    return json_response(
        status_code,
        {
            "error": error,
        },
        event=event,
    )
