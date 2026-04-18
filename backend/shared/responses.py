import json
from typing import Any, Dict


def json_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def error_response(status_code: int, code: str, message: str) -> Dict[str, Any]:
    return json_response(
        status_code,
        {
            "error": {
                "code": code,
                "message": message,
            }
        },
    )
