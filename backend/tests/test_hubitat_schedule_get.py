import json

import pytest

from functions.hubitat_schedule_get.handler import lambda_handler


class FakeSchedulesTable:
    def __init__(self, items):
        self.items = items

    def query(self, KeyConditionExpression=None):  # noqa: ARG002
        return {"Items": list(self.items)}


def _event(hub_id="hub-1", days="7", token="hub-token"):
    return {
        "headers": {"X-Hubitat-Token": token},
        "queryStringParameters": {"hubId": hub_id, "days": days},
    }


def _base_items():
    return [
        {
            "hubId": "hub-1",
            "itemKey": "META",
            "scheduleVersion": 3,
            "timezone": "America/New_York",
        },
        {
            "hubId": "hub-1",
            "itemKey": "EVT#2026-04-18#07:00#evt1",
            "eventId": "evt1",
            "date": "2026-04-18",
            "time": "07:00",
            "actionType": "rule",
            "parameters": {"targetId": "rule:1"},
            "sourceScheduleId": "wake",
        },
    ]


def test_compiled_events_only(monkeypatch):
    monkeypatch.setenv("HUBITAT_TOKEN", "hub-token")
    monkeypatch.setattr(
        "functions.hubitat_schedule_get.handler.get_schedules_table",
        lambda: FakeSchedulesTable(_base_items()),
    )
    monkeypatch.setattr(
        "functions.hubitat_schedule_get.handler._today_in_timezone",
        lambda tz: __import__("datetime").datetime(2026, 4, 18),
    )

    response = lambda_handler(_event(days="1"), None)

    assert response["statusCode"] == 200
    data = json.loads(response["body"])
    assert data["scheduleVersion"] == 3
    assert len(data["events"]) == 1


def test_compiled_and_broken_events(monkeypatch):
    items = _base_items() + [
        {
            "hubId": "hub-1",
            "itemKey": "BROKEN#2026-04-18#broken1",
            "eventId": "broken1",
            "date": "2026-04-18",
            "message": "Missing target",
            "originalLabel": "Wake",
            "sourceScheduleId": "wake",
        }
    ]

    monkeypatch.setenv("HUBITAT_TOKEN", "hub-token")
    monkeypatch.setattr(
        "functions.hubitat_schedule_get.handler.get_schedules_table",
        lambda: FakeSchedulesTable(items),
    )
    monkeypatch.setattr(
        "functions.hubitat_schedule_get.handler._today_in_timezone",
        lambda tz: __import__("datetime").datetime(2026, 4, 18),
    )

    response = lambda_handler(_event(days="1"), None)

    assert response["statusCode"] == 200
    data = json.loads(response["body"])
    assert len(data["events"]) == 2
    assert any("validation" in e for e in data["events"])


def test_empty_result(monkeypatch):
    monkeypatch.setenv("HUBITAT_TOKEN", "hub-token")
    monkeypatch.setattr(
        "functions.hubitat_schedule_get.handler.get_schedules_table",
        lambda: FakeSchedulesTable([{"hubId": "hub-1", "itemKey": "META", "timezone": "America/New_York"}]),
    )
    monkeypatch.setattr(
        "functions.hubitat_schedule_get.handler._today_in_timezone",
        lambda tz: __import__("datetime").datetime(2026, 4, 18),
    )

    response = lambda_handler(_event(days="1"), None)

    assert response["statusCode"] == 200
    data = json.loads(response["body"])
    assert data["events"] == []


def test_invalid_token(monkeypatch):
    monkeypatch.setenv("HUBITAT_TOKEN", "hub-token")

    response = lambda_handler(_event(token="bad"), None)

    assert response["statusCode"] == 401


def test_invalid_missing_hub_id(monkeypatch):
    monkeypatch.setenv("HUBITAT_TOKEN", "hub-token")
    event = _event()
    del event["queryStringParameters"]["hubId"]

    response = lambda_handler(event, None)

    assert response["statusCode"] == 400


@pytest.mark.parametrize("days", ["abc", "0", "91"])
def test_invalid_days_values(monkeypatch, days):
    monkeypatch.setenv("HUBITAT_TOKEN", "hub-token")

    response = lambda_handler(_event(days=days), None)

    assert response["statusCode"] == 400


def test_includes_past_events_from_current_day(monkeypatch):
    items = _base_items() + [
        {
            "hubId": "hub-1",
            "itemKey": "EVT#2026-04-18#01:00#evtPast",
            "eventId": "evtPast",
            "date": "2026-04-18",
            "time": "01:00",
            "actionType": "rule",
            "parameters": {"targetId": "rule:1"},
            "sourceScheduleId": "wake",
        }
    ]

    monkeypatch.setenv("HUBITAT_TOKEN", "hub-token")
    monkeypatch.setattr(
        "functions.hubitat_schedule_get.handler.get_schedules_table",
        lambda: FakeSchedulesTable(items),
    )
    monkeypatch.setattr(
        "functions.hubitat_schedule_get.handler._today_in_timezone",
        lambda tz: __import__("datetime").datetime(2026, 4, 18, 20, 0),
    )

    response = lambda_handler(_event(days="1"), None)

    assert response["statusCode"] == 200
    data = json.loads(response["body"])
    event_ids = [e["eventId"] for e in data["events"]]
    assert "evtPast" in event_ids
