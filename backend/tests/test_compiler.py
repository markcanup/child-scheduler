from datetime import date

import pytest

from shared.compiler import (
    CompilerValidationError,
    build_compile_dates,
    build_meta_item,
    compile_schedule,
    resolve_times_for_date,
    validate_resolved_action,
    validate_schedule_definitions,
)


def _catalog():
    return {
        "resources": [
            {"resourceId": "rule:1", "type": "rule", "label": "Rule 1"},
            {"resourceId": "speechTarget:1", "type": "speechTarget", "label": "Speaker"},
            {
                "resourceId": "notifyDevice:1",
                "type": "notifyDevice",
                "label": "Phone",
            },
        ]
    }


def _base_defs():
    return [
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
    ]


def test_validation_duplicate_schedule_id():
    defs = _base_defs() + [_base_defs()[0].copy()]
    with pytest.raises(CompilerValidationError, match="Duplicate scheduleId"):
        validate_schedule_definitions(defs)


def test_validation_invalid_time_mode():
    defs = _base_defs()
    defs[0]["timeMode"] = "bad"
    with pytest.raises(CompilerValidationError, match="Invalid timeMode"):
        validate_schedule_definitions(defs)


def test_validation_invalid_action_type():
    defs = _base_defs()
    defs[0]["actionType"] = "bad"
    with pytest.raises(CompilerValidationError, match="Invalid actionType"):
        validate_schedule_definitions(defs)


def test_validation_missing_required_fields():
    defs = _base_defs()
    del defs[0]["scheduleId"]
    with pytest.raises(CompilerValidationError, match="Missing required field"):
        validate_schedule_definitions(defs)


def test_validation_relative_reference_missing_schedule():
    defs = _base_defs()
    defs[1]["relativeToScheduleId"] = "missing"
    with pytest.raises(CompilerValidationError, match="Relative reference missing"):
        validate_schedule_definitions(defs)


def test_time_resolution_absolute_relative_and_chained():
    defs = _base_defs() + [
        {
            "scheduleId": "notify",
            "name": "Notify",
            "enabled": True,
            "daysOfWeek": ["MON"],
            "timeMode": "relative",
            "relativeToScheduleId": "speak",
            "offsetMinutes": 10,
            "actionType": "notify",
            "parameters": {"targetIds": ["notifyDevice:1"], "text": "Time to go"},
        }
    ]
    resolved = resolve_times_for_date(defs, date(2026, 4, 20), {"overrides": {}})
    times = [entry["time"] for entry in resolved]
    assert times == ["07:00", "07:05", "07:15"]


def test_time_resolution_uses_day_specific_absolute_times():
    defs = _base_defs()
    defs[0].pop("baseTime")
    defs[0]["dayTimes"] = {"MON": "07:00", "TUE": "08:30"}
    defs[0]["daysOfWeek"] = ["MON", "TUE"]
    defs[1]["daysOfWeek"] = []

    monday = compile_schedule(
        hub_id="hub-1",
        schedule_definitions=defs,
        day_configs=[],
        catalog=_catalog(),
        start_date=date(2026, 4, 20),
        days=1,
    )
    assert [event["time"] for event in monday["eventItems"]] == ["07:00", "07:05"]

    tuesday = compile_schedule(
        hub_id="hub-1",
        schedule_definitions=defs,
        day_configs=[],
        catalog=_catalog(),
        start_date=date(2026, 4, 21),
        days=1,
    )
    assert [event["time"] for event in tuesday["eventItems"]] == ["08:30", "08:35"]


def test_relative_schedule_applies_on_parent_days_without_its_own_days():
    defs = [
        {
            "scheduleId": "wake",
            "name": "Wake",
            "enabled": True,
            "dayTimes": {"TUE": "08:00"},
            "timeMode": "absolute",
            "actionType": "rule",
            "parameters": {"targetId": "rule:1"},
        },
        {
            "scheduleId": "announce",
            "name": "Announce",
            "enabled": True,
            "timeMode": "relative",
            "relativeToScheduleId": "wake",
            "offsetMinutes": 15,
            "actionType": "speech",
            "parameters": {"targetId": "speechTarget:1", "text": "Wake up"},
        },
    ]
    result = compile_schedule(
        hub_id="hub-1",
        schedule_definitions=defs,
        day_configs=[],
        catalog=_catalog(),
        start_date=date(2026, 4, 21),
        days=1,
    )
    assert [event["sourceScheduleId"] for event in result["eventItems"]] == ["wake", "announce"]
    assert [event["time"] for event in result["eventItems"]] == ["08:00", "08:15"]


def test_time_resolution_disabled_schedule_excluded():
    defs = _base_defs()
    defs[0]["enabled"] = False
    result = compile_schedule(
        hub_id="hub-1",
        schedule_definitions=defs,
        day_configs=[],
        catalog=_catalog(),
        start_date=date(2026, 4, 20),
        days=1,
    )
    assert result["eventItems"] == []


def test_time_resolution_day_override_time_override():
    defs = _base_defs()
    day_configs = [{"date": "2026-04-20", "overrides": {"wake": {"timeOverride": "08:00"}}}]
    result = compile_schedule(
        hub_id="hub-1",
        schedule_definitions=defs,
        day_configs=day_configs,
        catalog=_catalog(),
        start_date=date(2026, 4, 20),
        days=1,
    )
    assert [event["time"] for event in result["eventItems"]] == ["08:00", "08:05"]


def test_time_resolution_day_override_enabled_false():
    defs = _base_defs()
    day_configs = [{"date": "2026-04-20", "overrides": {"wake": {"enabled": False}}}]
    result = compile_schedule(
        hub_id="hub-1",
        schedule_definitions=defs,
        day_configs=day_configs,
        catalog=_catalog(),
        start_date=date(2026, 4, 20),
        days=1,
    )
    assert result["eventItems"] == []


def test_time_resolution_circular_dependency_detection_and_error_shape():
    defs = [
        {
            "scheduleId": "a",
            "name": "A",
            "enabled": True,
            "daysOfWeek": ["MON"],
            "timeMode": "relative",
            "relativeToScheduleId": "b",
            "offsetMinutes": 1,
            "actionType": "rule",
            "parameters": {"targetId": "rule:1"},
        },
        {
            "scheduleId": "b",
            "name": "B",
            "enabled": True,
            "daysOfWeek": ["MON"],
            "timeMode": "relative",
            "relativeToScheduleId": "a",
            "offsetMinutes": 1,
            "actionType": "rule",
            "parameters": {"targetId": "rule:1"},
        },
    ]

    with pytest.raises(CompilerValidationError) as exc_info:
        compile_schedule(
            hub_id="hub-1",
            schedule_definitions=defs,
            day_configs=[],
            catalog=_catalog(),
            start_date=date(2026, 4, 20),
            days=1,
        )

    error_shape = exc_info.value.as_error()
    assert error_shape["error"]["code"] == "VALIDATION_ERROR"


def test_action_validation_rule_speech_notify_valid():
    defs = _base_defs() + [
        {
            "scheduleId": "notify",
            "name": "Notify",
            "enabled": True,
            "daysOfWeek": ["MON"],
            "timeMode": "absolute",
            "baseTime": "09:00",
            "actionType": "notify",
            "parameters": {"targetIds": ["notifyDevice:1"], "text": "Hello"},
        }
    ]

    result = compile_schedule(
        hub_id="hub-1",
        schedule_definitions=defs,
        day_configs=[],
        catalog=_catalog(),
        start_date=date(2026, 4, 20),
        days=1,
    )
    assert len(result["eventItems"]) == 3
    assert len(result["brokenItems"]) == 0


def test_action_validation_missing_catalog_resource():
    d = _base_defs()[0]
    d["parameters"] = {"targetId": "rule:999"}
    message = validate_resolved_action(d, _catalog()["resources"] and {})
    assert "Missing catalog resource" in message


def test_action_validation_wrong_resource_type():
    d = _base_defs()[0]
    d["parameters"] = {"targetId": "speechTarget:1"}
    idx = {r["resourceId"]: r for r in _catalog()["resources"]}
    message = validate_resolved_action(d, idx)
    assert "Wrong resource type" in message


def test_action_validation_missing_text_and_empty_target_ids():
    speech = _base_defs()[1]
    speech["parameters"] = {"targetId": "speechTarget:1"}
    idx = {r["resourceId"]: r for r in _catalog()["resources"]}
    assert "Missing text" in validate_resolved_action(speech, idx)

    notify = {
        "scheduleId": "n",
        "actionType": "notify",
        "parameters": {"targetIds": [], "text": "x"},
    }
    assert "non-empty" in validate_resolved_action(notify, idx)


def test_compile_output_event_and_broken_items_and_preview_arrays():
    defs = _base_defs()
    defs[1]["parameters"] = {"targetId": "speechTarget:999", "text": "Hi"}
    result = compile_schedule(
        hub_id="hub-1",
        schedule_definitions=defs,
        day_configs=[],
        catalog=_catalog(),
        start_date=date(2026, 4, 20),
        days=1,
        schedule_version=4,
    )

    assert len(result["eventItems"]) == 1
    assert len(result["brokenItems"]) == 1
    assert result["compiledPreview"] == result["eventItems"]
    assert result["brokenReferences"] == result["brokenItems"]
    assert result["metaItem"]["scheduleVersion"] == 4


def test_build_compile_dates_and_meta_item():
    dates = build_compile_dates(date(2026, 4, 20), days=3)
    assert [d.isoformat() for d in dates] == ["2026-04-20", "2026-04-21", "2026-04-22"]

    meta = build_meta_item("hub-1", 9, "2026-04-20T00:00:00Z")
    assert meta["itemKey"] == "META"
    assert meta["timezone"] == "America/New_York"
