from typing import Any, Dict, List


class ValidationError(Exception):
    pass


REQUIRED_FIELDS = [
    "hubId",
    "generatedAt",
    "catalogVersion",
    "actionDefinitions",
    "resources",
]


def validate_action_catalog_payload(payload: Dict[str, Any]) -> None:
    missing = [field for field in REQUIRED_FIELDS if field not in payload]
    if missing:
        raise ValidationError(f"Missing required field(s): {', '.join(missing)}")

    resources = payload.get("resources")
    if not isinstance(resources, list):
        raise ValidationError("resources must be an array")

    seen = set()
    for resource in resources:
        if not isinstance(resource, dict):
            raise ValidationError("each resource must be an object")
        resource_id = resource.get("resourceId")
        if not resource_id:
            raise ValidationError("each resource must include resourceId")
        if resource_id in seen:
            raise ValidationError(f"Duplicate resourceId: {resource_id}")
        seen.add(resource_id)


def build_resource_index(resources: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {resource["resourceId"]: resource for resource in resources}
