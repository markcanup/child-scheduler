import json

from functions.hubitat_action_catalog_post.handler import lambda_handler


class FakeTable:
    def __init__(self):
        self.items = []

    def put_item(self, Item):
        self.items.append(Item)


def _valid_event(token="test-token"):
    body = {
        "hubId": "hub-1",
        "generatedAt": "2026-04-18T00:00:00Z",
        "catalogVersion": "v1",
        "actionDefinitions": [
            {"actionType": "rule", "label": "Run Rule"},
        ],
        "resources": [
            {"resourceId": "rule:1", "label": "Morning Rule", "type": "rule"},
            {
                "resourceId": "speechTarget:2",
                "label": "Bedroom Speaker",
                "type": "speechTarget",
            },
        ],
    }
    return {
        "headers": {"X-Hubitat-Token": token},
        "body": json.dumps(body),
    }


def test_happy_path(monkeypatch):
    fake_table = FakeTable()
    compile_calls = []

    monkeypatch.setenv("HUBITAT_TOKEN", "test-token")
    monkeypatch.setattr(
        "functions.hubitat_action_catalog_post.handler.get_action_catalogs_table",
        lambda: fake_table,
    )
    monkeypatch.setattr(
        "functions.hubitat_action_catalog_post.handler.compile_schedule",
        lambda **kwargs: compile_calls.append(kwargs),
    )

    response = lambda_handler(_valid_event(), None)

    assert response["statusCode"] == 200
    data = json.loads(response["body"])
    assert data["hubId"] == "hub-1"
    assert data["status"] == "ok"
    assert data["resourceCount"] == 2
    assert len(fake_table.items) == 1
    assert "resourceIndex" in fake_table.items[0]
    assert compile_calls == [{"hub_id": "hub-1", "reason": "catalog_updated"}]


def test_missing_required_fields(monkeypatch):
    monkeypatch.setenv("HUBITAT_TOKEN", "test-token")

    event = {
        "headers": {"X-Hubitat-Token": "test-token"},
        "body": json.dumps({"hubId": "hub-1"}),
    }

    response = lambda_handler(event, None)

    assert response["statusCode"] == 400
    data = json.loads(response["body"])
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_duplicate_resource_ids(monkeypatch):
    monkeypatch.setenv("HUBITAT_TOKEN", "test-token")
    event = _valid_event()
    body = json.loads(event["body"])
    body["resources"].append({"resourceId": "rule:1", "label": "dup", "type": "rule"})
    event["body"] = json.dumps(body)

    response = lambda_handler(event, None)

    assert response["statusCode"] == 400
    data = json.loads(response["body"])
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "Duplicate resourceId" in data["error"]["message"]


def test_invalid_token(monkeypatch):
    monkeypatch.setenv("HUBITAT_TOKEN", "test-token")

    response = lambda_handler(_valid_event(token="bad-token"), None)

    assert response["statusCode"] == 401
    data = json.loads(response["body"])
    assert data["error"]["code"] == "UNAUTHORIZED"


def test_recompile_triggered_on_catalog_change(monkeypatch):
    fake_table = FakeTable()
    compile_calls = []

    monkeypatch.setenv("HUBITAT_TOKEN", "test-token")
    monkeypatch.setattr(
        "functions.hubitat_action_catalog_post.handler.get_action_catalogs_table",
        lambda: fake_table,
    )

    def fake_compile(**kwargs):
        compile_calls.append(kwargs)
        return {"status": "queued"}

    monkeypatch.setattr(
        "functions.hubitat_action_catalog_post.handler.compile_schedule",
        fake_compile,
    )

    response = lambda_handler(_valid_event(), None)

    assert response["statusCode"] == 200
    assert len(compile_calls) == 1
    assert compile_calls[0]["hub_id"] == "hub-1"
