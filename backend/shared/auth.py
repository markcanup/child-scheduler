import os
from typing import Any, Dict, Optional


class AuthError(Exception):
    pass


def _get_header(event: Dict[str, Any], name: str) -> Optional[str]:
    headers = event.get("headers") or {}
    return headers.get(name) or headers.get(name.lower())


def validate_hubitat_token(event: Dict[str, Any]) -> None:
    expected_token = os.environ.get("HUBITAT_TOKEN", "")
    provided = _get_header(event, "X-Hubitat-Token")
    if not expected_token or provided != expected_token:
        raise AuthError("Invalid Hubitat token")


def _extract_jwt_claims(event: Dict[str, Any]) -> Dict[str, Any]:
    request_context = event.get("requestContext") or {}
    authorizer = request_context.get("authorizer") or {}
    jwt = authorizer.get("jwt") or {}
    claims = jwt.get("claims") or {}
    if isinstance(claims, dict):
        return claims
    return {}


def validate_ui_auth(event: Dict[str, Any]) -> Dict[str, Any]:
    """Validate browser auth for deployed (Cognito) and local-dev (stub token) modes."""
    claims = _extract_jwt_claims(event)
    if claims:
        return claims

    expected_token = os.environ.get("UI_JWT_STUB_TOKEN", "")
    auth_header = _get_header(event, "Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise AuthError("Unauthorized")

    token = auth_header.split(" ", 1)[1].strip()
    if expected_token and token != expected_token:
        raise AuthError("Unauthorized")

    return {}


def resolve_ui_hub_id(event: Dict[str, Any], claims: Optional[Dict[str, Any]] = None) -> str:
    """Single-user/single-hub resolver for v1 with optional Cognito claim mapping."""
    claims = claims or {}
    query = event.get("queryStringParameters") or {}

    hub_id = (
        query.get("hubId")
        or claims.get("custom:hubId")
        or claims.get("hubId")
        or os.environ.get("DEFAULT_HUB_ID")
    )

    if not hub_id:
        raise AuthError("Hub not resolved for authenticated UI user")
    return hub_id
