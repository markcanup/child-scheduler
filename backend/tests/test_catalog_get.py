import json

from functions.catalog_get.handler import lambda_handler


class FakeTable:
    def __init__(self, item=None):
        self.item = item

    def get_item(self, Key):
        if self.item and Key.get("hubId") == self.item.get("hubId"):
            return {"Item": self.item}
        return {}



def _event_with_claims(hub_id_claim="hub-claims"):
    return {
        "headers": {},
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": "user-1",
                        "custom:hubId": hub_id_claim,
                    }
                }
            }
        },
        "queryStringParameters": {},
    }


def _event(token="ui-token", hub_id=None, with_claims=True):
    event = {
        "headers": {"Authorization": f"Bearer {token}"},
        "queryStringParameters": {},
    }
    if with_claims:
        event["requestContext"] = {
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": "user-1",
                        "custom:hubId": "hub-1",
                    }
                }
            }
        }
    if hub_id:
        event["queryStringParameters"]["hubId"] = hub_id
    return event


def test_catalog_exists(monkeypatch):
    monkeypatch.setenv("DEFAULT_HUB_ID", "hub-1")

    item = {
        "hubId": "hub-1",
        "generatedAt": "2026-04-18T00:00:00Z",
        "catalogVersion": "v1",
        "actionDefinitions": [{"actionType": "rule"}],
        "resources": [{"resourceId": "rule:1", "type": "rule", "label": "Rule"}],
    }
    monkeypatch.setattr(
        "functions.catalog_get.handler.get_action_catalogs_table",
        lambda: FakeTable(item=item),
    )

    response = lambda_handler(_event(), None)

    assert response["statusCode"] == 200
    data = json.loads(response["body"])
    assert data["hubId"] == "hub-1"
    assert data["catalogVersion"] == "v1"


def test_catalog_missing(monkeypatch):
    monkeypatch.setenv("DEFAULT_HUB_ID", "hub-1")
    monkeypatch.setattr(
        "functions.catalog_get.handler.get_action_catalogs_table",
        lambda: FakeTable(item=None),
    )

    response = lambda_handler(_event(), None)

    assert response["statusCode"] == 404
    data = json.loads(response["body"])
    assert data["error"]["code"] == "NOT_FOUND"


def test_unauthorized_request(monkeypatch):
    monkeypatch.delenv("COGNITO_ISSUER_URL", raising=False)

    response = lambda_handler(_event(token="wrong-token", with_claims=False), None)

    assert response["statusCode"] == 401
    data = json.loads(response["body"])
    assert data["error"]["code"] == "UNAUTHORIZED"


def test_catalog_exists_with_cognito_claims(monkeypatch):
    monkeypatch.setenv("DEFAULT_HUB_ID", "hub-default")

    item = {
        "hubId": "hub-claims",
        "generatedAt": "2026-04-18T00:00:00Z",
        "catalogVersion": "v1",
        "actionDefinitions": [{"actionType": "rule"}],
        "resources": [{"resourceId": "rule:1", "type": "rule", "label": "Rule"}],
    }
    monkeypatch.setattr(
        "functions.catalog_get.handler.get_action_catalogs_table",
        lambda: FakeTable(item=item),
    )

    response = lambda_handler(_event_with_claims(), None)

    assert response["statusCode"] == 200
    data = json.loads(response["body"])
    assert data["hubId"] == "hub-claims"
