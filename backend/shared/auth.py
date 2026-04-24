import base64
import json
import os
import time
from typing import Any, Dict, Optional, Tuple


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
    jwt_context = authorizer.get("jwt") or {}
    claims = jwt_context.get("claims") or {}
    if isinstance(claims, dict):
        return claims
    return {}


def _b64url_json_decode(value: str, error_message: str) -> Dict[str, Any]:
    padded = value + "=" * (-len(value) % 4)
    try:
        decoded = base64.urlsafe_b64decode(padded.encode("utf-8"))
        parsed = json.loads(decoded)
    except Exception as exc:  # noqa: BLE001
        raise AuthError(error_message) from exc

    if not isinstance(parsed, dict):
        raise AuthError(error_message)
    return parsed


def _decode_unverified_jwt(token: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    parts = token.split(".")
    if len(parts) != 3:
        raise AuthError("Unauthorized: bearer token is not a JWT")

    header = _b64url_json_decode(parts[0], "Unauthorized: bearer token header is invalid")
    claims = _b64url_json_decode(parts[1], "Unauthorized: bearer token payload is invalid")
    return header, claims


def _validate_expiration(claims: Dict[str, Any]) -> None:
    exp = claims.get("exp")
    if not isinstance(exp, (int, float)):
        raise AuthError("Unauthorized: token exp claim missing")
    if int(exp) <= int(time.time()):
        raise AuthError("Unauthorized: token is expired")


def _validate_cognito_claims(header: Dict[str, Any], claims: Dict[str, Any]) -> Dict[str, Any]:
    issuer = os.environ.get("COGNITO_ISSUER_URL", "").strip()
    app_client_id = os.environ.get("COGNITO_APP_CLIENT_ID", "").strip()

    if not issuer:
        raise AuthError("Unauthorized: missing COGNITO_ISSUER_URL backend configuration")

    if str(claims.get("iss", "")).rstrip("/") != issuer.rstrip("/"):
        raise AuthError("Unauthorized: token issuer does not match COGNITO_ISSUER_URL")

    alg = str(header.get("alg", ""))
    if alg.lower() == "none" or not alg:
        raise AuthError("Unauthorized: unsupported JWT algorithm")

    _validate_expiration(claims)

    token_use = str(claims.get("token_use", "")).strip().lower()
    if token_use not in {"id", "access"}:
        raise AuthError("Unauthorized: token_use must be id or access")

    if app_client_id:
        if token_use == "id":
            audience = claims.get("aud")
            if isinstance(audience, list):
                match = app_client_id in audience
            else:
                match = str(audience) == app_client_id
            if not match:
                raise AuthError("Unauthorized: id token aud does not match configured app client")
        elif str(claims.get("client_id", "")) != app_client_id:
            raise AuthError("Unauthorized: access token client_id does not match configured app client")

    return claims


def _extract_bearer_token(event: Dict[str, Any]) -> str:
    auth_header = _get_header(event, "Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise AuthError("Unauthorized: missing bearer token")

    token = auth_header.split(" ", 1)[1].strip()
    if not token:
        raise AuthError("Unauthorized: missing bearer token")
    return token


def validate_ui_auth(event: Dict[str, Any]) -> Dict[str, Any]:
    """Validate browser auth via API Gateway Cognito claims or direct Cognito JWT claim checks."""
    claims = _extract_jwt_claims(event)
    if claims:
        return claims

    token = _extract_bearer_token(event)
    header, token_claims = _decode_unverified_jwt(token)
    return _validate_cognito_claims(header, token_claims)


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
