import os
from typing import Any, Dict


class AuthError(Exception):
    pass


def validate_hubitat_token(event: Dict[str, Any]) -> None:
    expected_token = os.environ.get("HUBITAT_TOKEN", "")
    headers = event.get("headers") or {}

    provided = headers.get("X-Hubitat-Token") or headers.get("x-hubitat-token")
    if not expected_token or provided != expected_token:
        raise AuthError("Invalid Hubitat token")


def validate_ui_auth(event: Dict[str, Any]) -> None:
    """JWT auth integration point (stub for Milestone 2)."""
    expected_token = os.environ.get("UI_JWT_STUB_TOKEN", "")
    headers = event.get("headers") or {}
    auth_header = headers.get("Authorization") or headers.get("authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise AuthError("Unauthorized")

    token = auth_header.split(" ", 1)[1].strip()
    if expected_token and token != expected_token:
        raise AuthError("Unauthorized")


def resolve_ui_hub_id(event: Dict[str, Any]) -> str:
    """Single-user/single-hub resolver for v1 until full Cognito mapping."""
    query = event.get("queryStringParameters") or {}
    hub_id = query.get("hubId") or os.environ.get("DEFAULT_HUB_ID")

    if not hub_id:
        raise AuthError("Hub not resolved for authenticated UI user")
    return hub_id
