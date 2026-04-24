import base64
import json
import time

import pytest

from shared.auth import AuthError, validate_ui_auth


def _jwt(claims):
    header = {"alg": "RS256", "typ": "JWT"}

    def encode_part(value):
        raw = json.dumps(value, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")

    return f"{encode_part(header)}.{encode_part(claims)}.signature"


def test_validate_ui_auth_uses_authorizer_claims():
    event = {
        "headers": {},
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": "user-1",
                        "custom:hubId": "hub-1",
                    }
                }
            }
        },
    }

    claims = validate_ui_auth(event)

    assert claims["sub"] == "user-1"


def test_validate_ui_auth_verifies_cognito_token_claims(monkeypatch):
    now = int(time.time())
    token = _jwt(
        {
            "iss": "https://issuer.example",
            "exp": now + 3600,
            "iat": now,
            "token_use": "id",
            "aud": "app-client-123",
            "sub": "user-123",
        }
    )

    event = {
        "headers": {"Authorization": f"Bearer {token}"},
    }

    monkeypatch.setenv("COGNITO_ISSUER_URL", "https://issuer.example")
    monkeypatch.setenv("COGNITO_APP_CLIENT_ID", "app-client-123")

    claims = validate_ui_auth(event)

    assert claims["sub"] == "user-123"


def test_validate_ui_auth_unauthorized_when_missing_bearer(monkeypatch):
    monkeypatch.setenv("COGNITO_ISSUER_URL", "https://issuer.example")

    with pytest.raises(AuthError):
        validate_ui_auth({"headers": {}})
