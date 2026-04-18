from typing import Any, Dict


def compile_schedule(*, hub_id: str, reason: str) -> Dict[str, Any]:
    """Compile schedule output for a hub.

    Placeholder for Milestone 4+, currently used as an integration point.
    """
    return {"hubId": hub_id, "reason": reason, "status": "queued"}
