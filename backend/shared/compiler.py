from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

VALID_ACTION_TYPES = {"rule", "speech", "notify"}
VALID_TIME_MODES = {"absolute", "relative"}
VALID_DAYS = {"MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"}
WEEKDAY_ORDER = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


@dataclass
class CompilerValidationError(Exception):
    message: str
    code: str = "VALIDATION_ERROR"

    def as_error(self) -> Dict[str, Dict[str, str]]:
        return {"error": {"code": self.code, "message": self.message}}


def _parse_time(value: str) -> Tuple[int, int]:
    try:
        hours_str, mins_str = value.split(":")
        hours = int(hours_str)
        mins = int(mins_str)
    except Exception as exc:  # noqa: BLE001
        raise CompilerValidationError(f"Invalid time format: {value}") from exc

    if hours < 0 or hours > 23 or mins < 0 or mins > 59:
        raise CompilerValidationError(f"Invalid time format: {value}")
    return hours, mins


def _format_time(hours: int, mins: int) -> str:
    total = (hours * 60 + mins) % (24 * 60)
    h = total // 60
    m = total % 60
    return f"{h:02d}:{m:02d}"


def _add_minutes(base_time: str, offset: int) -> str:
    hours, mins = _parse_time(base_time)
    return _format_time(hours, mins + offset)


def validate_schedule_definitions(schedule_definitions: List[Dict[str, Any]]) -> None:
    seen = set()

    for definition in schedule_definitions:
        schedule_id = definition.get("scheduleId")
        if not schedule_id:
            raise CompilerValidationError("Missing required field: scheduleId")
        if schedule_id in seen:
            raise CompilerValidationError(f"Duplicate scheduleId: {schedule_id}")
        seen.add(schedule_id)

        time_mode = definition.get("timeMode")
        if time_mode not in VALID_TIME_MODES:
            raise CompilerValidationError(f"Invalid timeMode for {schedule_id}: {time_mode}")

        action_type = definition.get("actionType")
        if action_type not in VALID_ACTION_TYPES:
            raise CompilerValidationError(f"Invalid actionType for {schedule_id}: {action_type}")

        if not isinstance(definition.get("parameters"), dict):
            raise CompilerValidationError(f"Missing required field: parameters for {schedule_id}")

        if time_mode == "absolute":
            day_times = definition.get("dayTimes")
            if day_times is None:
                # Backward-compatible path: daysOfWeek + baseTime
                days_of_week = definition.get("daysOfWeek")
                if not isinstance(days_of_week, list) or not days_of_week:
                    raise CompilerValidationError(
                        f"Missing required field: daysOfWeek for {schedule_id}"
                    )
                for day in days_of_week:
                    if day not in VALID_DAYS:
                        raise CompilerValidationError(f"Invalid day value for {schedule_id}: {day}")

                if not definition.get("baseTime"):
                    raise CompilerValidationError(f"Missing required field: baseTime for {schedule_id}")
                _parse_time(definition["baseTime"])
            else:
                if not isinstance(day_times, dict) or not day_times:
                    raise CompilerValidationError(
                        f"Missing required field: dayTimes for {schedule_id}"
                    )
                for day, time_value in day_times.items():
                    if day not in VALID_DAYS:
                        raise CompilerValidationError(f"Invalid day value for {schedule_id}: {day}")
                    _parse_time(time_value)
        else:
            if not definition.get("relativeToScheduleId"):
                raise CompilerValidationError(
                    f"Missing required field: relativeToScheduleId for {schedule_id}"
                )
            if not isinstance(definition.get("offsetMinutes", 0), int):
                raise CompilerValidationError(f"Invalid offsetMinutes for {schedule_id}")

    schedule_ids = {definition["scheduleId"] for definition in schedule_definitions}
    for definition in schedule_definitions:
        if definition.get("timeMode") == "relative":
            relative_id = definition.get("relativeToScheduleId")
            if relative_id not in schedule_ids:
                raise CompilerValidationError(
                    f"Relative reference missing for {definition['scheduleId']}: {relative_id}"
                )


def validate_day_configs(day_configs: List[Dict[str, Any]]) -> None:
    for config in day_configs:
        if "date" not in config:
            raise CompilerValidationError("Missing required field: date in dayConfigs")
        overrides = config.get("overrides", {})
        if not isinstance(overrides, dict):
            raise CompilerValidationError("dayConfig overrides must be an object")


def build_catalog_index(catalog: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    resources = (catalog or {}).get("resources", [])
    return {resource["resourceId"]: resource for resource in resources if "resourceId" in resource}


def build_compile_dates(start_date: date, days: int = 7) -> List[date]:
    return [start_date + timedelta(days=offset) for offset in range(days)]


def build_effective_day_config(compile_date: date, day_configs: List[Dict[str, Any]]) -> Dict[str, Any]:
    key = compile_date.isoformat()
    for config in day_configs:
        if config.get("date") == key:
            return config
    return {"date": key, "overrides": {}}


def get_applicable_schedule_definitions(
    schedule_definitions: List[Dict[str, Any]], compile_date: date, day_config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    weekday = WEEKDAY_ORDER[compile_date.weekday()]
    overrides = day_config.get("overrides", {})

    applicable = []
    for definition in schedule_definitions:
        if not definition.get("enabled", True):
            continue

        schedule_id = definition["scheduleId"]
        override = overrides.get(schedule_id, {})
        if override.get("enabled") is False:
            continue

        if definition.get("timeMode") == "relative":
            applicable.append(definition)
            continue

        day_times = definition.get("dayTimes")
        if isinstance(day_times, dict):
            if weekday not in day_times:
                continue
        elif weekday not in definition.get("daysOfWeek", []):
            continue

        applicable.append(definition)

    return applicable


def resolve_times_for_date(
    definitions: List[Dict[str, Any]], compile_date: date, day_config: Dict[str, Any]
) -> List[Dict[str, Any]]:
    by_id = {definition["scheduleId"]: definition for definition in definitions}
    overrides = day_config.get("overrides", {})
    resolved: Dict[str, str] = {}
    visiting = set()

    def resolve(schedule_id: str) -> str:
        if schedule_id in resolved:
            return resolved[schedule_id]
        if schedule_id in visiting:
            raise CompilerValidationError("Circular relative schedule dependency detected")

        visiting.add(schedule_id)
        definition = by_id[schedule_id]
        override = overrides.get(schedule_id, {})

        if override.get("enabled") is False:
            visiting.remove(schedule_id)
            raise CompilerValidationError(f"Schedule disabled by override: {schedule_id}")

        if "timeOverride" in override:
            time_value = override["timeOverride"]
            _parse_time(time_value)
            resolved[schedule_id] = time_value
            visiting.remove(schedule_id)
            return time_value

        if definition["timeMode"] == "absolute":
            day_times = definition.get("dayTimes")
            if isinstance(day_times, dict):
                weekday = WEEKDAY_ORDER[compile_date.weekday()]
                if weekday not in day_times:
                    visiting.remove(schedule_id)
                    raise CompilerValidationError(
                        f"No absolute time configured for {schedule_id} on {weekday}"
                    )
                time_value = day_times[weekday]
            else:
                time_value = definition["baseTime"]
        else:
            parent_id = definition["relativeToScheduleId"]
            if parent_id not in by_id:
                visiting.remove(schedule_id)
                raise CompilerValidationError(
                    f"Relative reference unavailable for {schedule_id}: {parent_id}"
                )
            parent_time = resolve(parent_id)
            time_value = _add_minutes(parent_time, definition.get("offsetMinutes", 0))

        resolved[schedule_id] = time_value
        visiting.remove(schedule_id)
        return time_value

    output = []
    for schedule_id, definition in by_id.items():
        try:
            output.append({"definition": definition, "time": resolve(schedule_id)})
        except CompilerValidationError as exc:
            if str(exc).startswith("Schedule disabled by override") or str(exc).startswith(
                "Relative reference unavailable"
            ):
                continue
            raise

    output.sort(key=lambda entry: entry["time"])
    return output


def validate_resolved_action(
    definition: Dict[str, Any], catalog_index: Dict[str, Dict[str, Any]]
) -> Optional[str]:
    action_type = definition["actionType"]
    parameters = definition.get("parameters", {})

    if action_type == "rule":
        target_id = parameters.get("targetId")
        if not target_id:
            return "Missing targetId for rule action"
        resource = catalog_index.get(target_id)
        if not resource:
            return f"Missing catalog resource: {target_id}"
        if resource.get("type") != "rule":
            return f"Wrong resource type for {target_id}; expected rule"
        return None

    if action_type == "speech":
        target_id = parameters.get("targetId")
        text = parameters.get("text")
        if not target_id:
            return "Missing targetId for speech action"
        if not text:
            return "Missing text for speech action"
        resource = catalog_index.get(target_id)
        if not resource:
            return f"Missing catalog resource: {target_id}"
        if resource.get("type") != "speechTarget":
            return f"Wrong resource type for {target_id}; expected speechTarget"
        return None

    if action_type == "notify":
        target_ids = parameters.get("targetIds")
        text = parameters.get("text")
        if not isinstance(target_ids, list) or len(target_ids) == 0:
            return "targetIds must be a non-empty array for notify action"
        if not text:
            return "Missing text for notify action"
        for target_id in target_ids:
            resource = catalog_index.get(target_id)
            if not resource:
                return f"Missing catalog resource: {target_id}"
            if resource.get("type") != "notifyDevice":
                return f"Wrong resource type for {target_id}; expected notifyDevice"
        return None

    return f"Unsupported actionType: {action_type}"


def build_meta_item(
    hub_id: str, schedule_version: int, compiled_at: str, timezone: str = "America/New_York"
) -> Dict[str, Any]:
    return {
        "hubId": hub_id,
        "itemKey": "META",
        "scheduleVersion": schedule_version,
        "compiledAt": compiled_at,
        "timezone": timezone,
    }


def build_definition_item(hub_id: str, definition: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "hubId": hub_id,
        "itemKey": f"DEF#{definition['scheduleId']}",
        **definition,
    }


def build_day_item(hub_id: str, day_config: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "hubId": hub_id,
        "itemKey": f"DAY#{day_config['date']}",
        **day_config,
    }


def build_compiled_event_item(
    hub_id: str, compile_date: date, time_value: str, definition: Dict[str, Any]
) -> Dict[str, Any]:
    date_str = compile_date.isoformat()
    event_id = f"{date_str}#{time_value}#{definition['scheduleId']}"
    return {
        "hubId": hub_id,
        "itemKey": f"EVT#{date_str}#{time_value}#{event_id}",
        "eventId": event_id,
        "date": date_str,
        "time": time_value,
        "actionType": definition["actionType"],
        "parameters": definition["parameters"],
        "sourceScheduleId": definition["scheduleId"],
    }


def build_broken_item(
    hub_id: str,
    compile_date: date,
    definition: Dict[str, Any],
    message: str,
    original_label: Optional[str] = None,
) -> Dict[str, Any]:
    date_str = compile_date.isoformat()
    event_id = f"broken#{date_str}#{definition['scheduleId']}"
    return {
        "hubId": hub_id,
        "itemKey": f"BROKEN#{date_str}#{event_id}",
        "eventId": event_id,
        "date": date_str,
        "message": message,
        "originalLabel": original_label or definition.get("name", definition["scheduleId"]),
        "sourceScheduleId": definition["scheduleId"],
    }


def compile_schedule(
    *,
    hub_id: str,
    schedule_definitions: Optional[List[Dict[str, Any]]] = None,
    day_configs: Optional[List[Dict[str, Any]]] = None,
    catalog: Optional[Dict[str, Any]] = None,
    schedule_version: int = 1,
    timezone: str = "America/New_York",
    start_date: Optional[date] = None,
    days: int = 7,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    if schedule_definitions is None:
        return {"hubId": hub_id, "status": "queued", "reason": reason}

    day_configs = day_configs or []
    validate_schedule_definitions(schedule_definitions)
    validate_day_configs(day_configs)

    catalog_index = build_catalog_index(catalog)
    compile_start = start_date or date.today()
    compile_dates = build_compile_dates(compile_start, days=days)

    definition_items = [build_definition_item(hub_id, d) for d in schedule_definitions]
    day_items = [build_day_item(hub_id, d) for d in day_configs]

    event_items: List[Dict[str, Any]] = []
    broken_items: List[Dict[str, Any]] = []

    for compile_date in compile_dates:
        day_config = build_effective_day_config(compile_date, day_configs)
        applicable = get_applicable_schedule_definitions(
            schedule_definitions, compile_date, day_config
        )
        resolved = resolve_times_for_date(applicable, compile_date, day_config)

        for entry in resolved:
            definition = entry["definition"]
            time_value = entry["time"]
            validation_error = validate_resolved_action(definition, catalog_index)
            if validation_error:
                broken_items.append(
                    build_broken_item(hub_id, compile_date, definition, validation_error)
                )
                continue

            event_items.append(build_compiled_event_item(hub_id, compile_date, time_value, definition))

    compiled_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )
    meta_item = build_meta_item(hub_id, schedule_version, compiled_at, timezone=timezone)

    return {
        "metaItem": meta_item,
        "definitionItems": definition_items,
        "dayItems": day_items,
        "eventItems": event_items,
        "brokenItems": broken_items,
        "compiledPreview": event_items,
        "brokenReferences": broken_items,
    }
