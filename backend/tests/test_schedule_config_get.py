import json
from decimal import Decimal

from functions.schedule_config_get.handler import lambda_handler


class FakeTable:
    def __init__(self, items):
        self.items = items


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


def test_empty_hub_state(monkeypatch):
    monkeypatch.setenv("UI_JWT_STUB_TOKEN", "ui-token")
    monkeypatch.setenv("DEFAULT_HUB_ID", "hub-1")
    monkeypatch.setenv("HUBITAT_TOKEN_LAST_ROTATED", "2026-04-23.18:20:12")
    monkeypatch.setattr(
        "functions.schedule_config_get.handler.get_schedules_table",
        lambda: FakeTable(items=[]),
    )
    monkeypatch.setattr(
        "functions.schedule_config_get.handler._query_schedule_items",
        lambda table, hub_id: [],
    )

    response = lambda_handler(_event(), None)

    assert response["statusCode"] == 200
    data = json.loads(response["body"])
    assert data["hubId"] == "hub-1"
    assert data["meta"]["timezone"] == "America/New_York"
    assert data["scheduleDefinitions"] == []
    assert data["dayConfigs"] == []
    assert data["compiledPreview"] == []
    assert data["brokenReferences"] == []
    assert data["security"]["hubitatTokenLastRotatedAt"] == "2026-04-23T18:20:12Z"


def test_populated_hub_state(monkeypatch):
    monkeypatch.setenv("UI_JWT_STUB_TOKEN", "ui-token")
    monkeypatch.setenv("DEFAULT_HUB_ID", "hub-1")
    monkeypatch.setenv("HUBITAT_TOKEN_LAST_ROTATED", "2026-04-23.18:20:12")

    items = [
        {
            "hubId": "hub-1",
            "itemKey": "META",
            "scheduleVersion": 3,
            "compiledAt": "2026-04-18T12:00:00Z",
            "timezone": "America/New_York",
        },
        {"hubId": "hub-1", "itemKey": "DEF#morning", "scheduleId": "morning"},
        {"hubId": "hub-1", "itemKey": "DAY#2026-04-18", "date": "2026-04-18"},
        {
            "hubId": "hub-1",
            "itemKey": "EVT#2026-04-18#07:00#evt1",
            "eventId": "evt1",
        },
        {
            "hubId": "hub-1",
            "itemKey": "BROKEN#2026-04-18#evt2",
            "eventId": "evt2",
        },
    ]

    monkeypatch.setattr(
        "functions.schedule_config_get.handler.get_schedules_table",
        lambda: FakeTable(items=items),
    )
    monkeypatch.setattr(
        "functions.schedule_config_get.handler._query_schedule_items",
        lambda table, hub_id: items,
    )

    response = lambda_handler(_event(), None)

    assert response["statusCode"] == 200
    data = json.loads(response["body"])
    assert data["meta"]["scheduleVersion"] == 3
    assert len(data["scheduleDefinitions"]) == 1
    assert len(data["dayConfigs"]) == 1
    assert len(data["compiledPreview"]) == 1
    assert len(data["brokenReferences"]) == 1
    assert data["security"]["hubitatTokenLastRotatedAt"] == "2026-04-23T18:20:12Z"


def test_populated_hub_state_normalizes_decimal_fields(monkeypatch):
    monkeypatch.setenv("UI_JWT_STUB_TOKEN", "ui-token")
    monkeypatch.setenv("DEFAULT_HUB_ID", "hub-1")

    items = [
        {
            "hubId": "hub-1",
            "itemKey": "META",
            "scheduleVersion": Decimal("4"),
            "compiledAt": "2026-04-18T12:00:00Z",
            "timezone": "America/New_York",
        },
        {
            "hubId": "hub-1",
            "itemKey": "DEF#relative",
            "scheduleId": "relative",
            "offsetMinutes": Decimal("5"),
        },
    ]

    monkeypatch.setattr(
        "functions.schedule_config_get.handler.get_schedules_table",
        lambda: FakeTable(items=items),
    )
    monkeypatch.setattr(
        "functions.schedule_config_get.handler._query_schedule_items",
        lambda table, hub_id: items,
    )

    response = lambda_handler(_event(), None)

    assert response["statusCode"] == 200
    data = json.loads(response["body"])
    assert data["meta"]["scheduleVersion"] == 4
    assert data["scheduleDefinitions"][0]["offsetMinutes"] == 5


def test_invalid_rotation_timestamp_returns_null(monkeypatch):
    monkeypatch.setenv("UI_JWT_STUB_TOKEN", "ui-token")
    monkeypatch.setenv("DEFAULT_HUB_ID", "hub-1")
    monkeypatch.setenv("HUBITAT_TOKEN_LAST_ROTATED", "not-a-date")
    monkeypatch.setattr(
        "functions.schedule_config_get.handler.get_schedules_table",
        lambda: FakeTable(items=[]),
    )
    monkeypatch.setattr(
        "functions.schedule_config_get.handler._query_schedule_items",
        lambda table, hub_id: [],
    )

    response = lambda_handler(_event(), None)

    assert response["statusCode"] == 200
    data = json.loads(response["body"])
    assert data["security"]["hubitatTokenLastRotatedAt"] is None


def test_unauthorized_request(monkeypatch):
    monkeypatch.setenv("UI_JWT_STUB_TOKEN", "ui-token")

    response = lambda_handler(_event(token="wrong-token", with_claims=False), None)

    assert response["statusCode"] == 401
    data = json.loads(response["body"])
    assert data["error"]["code"] == "UNAUTHORIZED"
