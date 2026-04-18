import json

from functions.schedule_config_put.handler import lambda_handler


class FakeCatalogTable:
    def __init__(self, item=None):
        self.item = item

    def get_item(self, Key):
        if self.item and Key.get("hubId") == self.item.get("hubId"):
            return {"Item": self.item}
        return {}


class FakeSchedulesTable:
    def __init__(self, items=None):
        self.items = list(items or [])

    def get_item(self, Key):
        for item in self.items:
            if item.get("hubId") == Key.get("hubId") and item.get("itemKey") == Key.get("itemKey"):
                return {"Item": item}
        return {}

    def query(self, KeyConditionExpression=None):  # noqa: ARG002
        return {"Items": list(self.items)}

    def delete_item(self, Key):
        self.items = [
            item
            for item in self.items
            if not (item.get("hubId") == Key.get("hubId") and item.get("itemKey") == Key.get("itemKey"))
        ]

    def put_item(self, Item):
        self.delete_item({"hubId": Item["hubId"], "itemKey": Item["itemKey"]})
        self.items.append(Item)


def _event(body, token="ui-token"):
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "queryStringParameters": {"hubId": "hub-1"},
        "body": json.dumps(body),
    }


def _payload():
    return {
        "hubId": "hub-1",
        "meta": {},
        "scheduleDefinitions": [
            {
                "scheduleId": "wake",
                "name": "Wake",
                "enabled": True,
                "daysOfWeek": ["MON"],
                "timeMode": "absolute",
                "baseTime": "07:00",
                "actionType": "rule",
                "parameters": {"targetId": "rule:1"},
            },
            {
                "scheduleId": "speak",
                "name": "Speak",
                "enabled": True,
                "daysOfWeek": ["MON"],
                "timeMode": "relative",
                "relativeToScheduleId": "wake",
                "offsetMinutes": 5,
                "actionType": "speech",
                "parameters": {"targetId": "speechTarget:1", "text": "Good morning"},
            },
        ],
        "dayConfigs": [],
    }


def _catalog_item():
    return {
        "hubId": "hub-1",
        "resources": [
            {"resourceId": "rule:1", "type": "rule", "label": "Rule 1"},
            {"resourceId": "speechTarget:1", "type": "speechTarget", "label": "Speaker"},
        ],
    }


def test_full_happy_path(monkeypatch):
    schedules_table = FakeSchedulesTable(items=[])

    monkeypatch.setenv("UI_JWT_STUB_TOKEN", "ui-token")
    monkeypatch.setattr(
        "functions.schedule_config_put.handler.get_action_catalogs_table",
        lambda: FakeCatalogTable(item=_catalog_item()),
    )
    monkeypatch.setattr(
        "functions.schedule_config_put.handler.get_schedules_table",
        lambda: schedules_table,
    )

    response = lambda_handler(_event(_payload()), None)

    assert response["statusCode"] == 200
    data = json.loads(response["body"])
    assert data["hubId"] == "hub-1"
    assert data["status"] == "ok"
    assert data["scheduleVersion"] == 1
    assert len(data["compiledPreview"]) >= 1


def test_validation_failure(monkeypatch):
    monkeypatch.setenv("UI_JWT_STUB_TOKEN", "ui-token")
    monkeypatch.setattr(
        "functions.schedule_config_put.handler.get_action_catalogs_table",
        lambda: FakeCatalogTable(item=_catalog_item()),
    )
    monkeypatch.setattr(
        "functions.schedule_config_put.handler.get_schedules_table",
        lambda: FakeSchedulesTable(items=[]),
    )

    response = lambda_handler(_event({"hubId": "hub-1"}), None)

    assert response["statusCode"] == 400
    data = json.loads(response["body"])
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_no_action_catalog_present(monkeypatch):
    monkeypatch.setenv("UI_JWT_STUB_TOKEN", "ui-token")
    monkeypatch.setattr(
        "functions.schedule_config_put.handler.get_action_catalogs_table",
        lambda: FakeCatalogTable(item=None),
    )
    monkeypatch.setattr(
        "functions.schedule_config_put.handler.get_schedules_table",
        lambda: FakeSchedulesTable(items=[]),
    )

    response = lambda_handler(_event(_payload()), None)

    assert response["statusCode"] == 400
    data = json.loads(response["body"])
    assert "No action catalog present" in data["error"]["message"]


def test_broken_references_generated(monkeypatch):
    schedules_table = FakeSchedulesTable(items=[])
    payload = _payload()
    payload["scheduleDefinitions"][1]["parameters"]["targetId"] = "speechTarget:999"

    monkeypatch.setenv("UI_JWT_STUB_TOKEN", "ui-token")
    monkeypatch.setattr(
        "functions.schedule_config_put.handler.get_action_catalogs_table",
        lambda: FakeCatalogTable(item=_catalog_item()),
    )
    monkeypatch.setattr(
        "functions.schedule_config_put.handler.get_schedules_table",
        lambda: schedules_table,
    )

    response = lambda_handler(_event(payload), None)

    assert response["statusCode"] == 200
    data = json.loads(response["body"])
    assert len(data["brokenReferences"]) == 1


def test_relative_schedule_compilation(monkeypatch):
    schedules_table = FakeSchedulesTable(items=[])

    monkeypatch.setenv("UI_JWT_STUB_TOKEN", "ui-token")
    monkeypatch.setattr(
        "functions.schedule_config_put.handler.get_action_catalogs_table",
        lambda: FakeCatalogTable(item=_catalog_item()),
    )
    monkeypatch.setattr(
        "functions.schedule_config_put.handler.get_schedules_table",
        lambda: schedules_table,
    )

    response = lambda_handler(_event(_payload()), None)

    assert response["statusCode"] == 200
    data = json.loads(response["body"])
    times = [evt["time"] for evt in data["compiledPreview"]]
    assert "07:00" in times
    assert "07:05" in times


def test_overwrite_previous_window(monkeypatch):
    existing_items = [
        {"hubId": "hub-1", "itemKey": "META", "scheduleVersion": 1},
        {"hubId": "hub-1", "itemKey": "EVT#2026-04-20#07:00#old", "eventId": "old"},
        {"hubId": "hub-1", "itemKey": "BROKEN#2026-04-20#old", "eventId": "old"},
    ]
    schedules_table = FakeSchedulesTable(items=existing_items)

    monkeypatch.setenv("UI_JWT_STUB_TOKEN", "ui-token")
    monkeypatch.setattr(
        "functions.schedule_config_put.handler.get_action_catalogs_table",
        lambda: FakeCatalogTable(item=_catalog_item()),
    )
    monkeypatch.setattr(
        "functions.schedule_config_put.handler.get_schedules_table",
        lambda: schedules_table,
    )

    response = lambda_handler(_event(_payload()), None)

    assert response["statusCode"] == 200
    keys = {item["itemKey"] for item in schedules_table.items}
    assert "EVT#2026-04-20#07:00#old" not in keys
    assert "BROKEN#2026-04-20#old" not in keys
