from typing import Any

from httpx import Response as HTTPResponse


def extract_http_response_body(response: HTTPResponse) -> Any:
    try:
        return response.json()
    except Exception:  # noqa
        return response.text
