from typing import Any

from psycopg.types.json import Jsonb

from ...conf import constants


def parse_values(cast_json: bool = True, **kwargs) -> dict[str, Any]:
    """
    Parse values for SQL queries, casting JSON fields if necessary.
    """
    return {
        key: Jsonb(value)
        if isinstance(value, (list, dict)) and cast_json
        else value
        for key, value in kwargs.items()
    }


def parse_filter(key: str) -> tuple[str, str]:
    """
    Parse filter keys into SQL field and operator.
    """
    parts = key.split("__")
    field = parts[0]
    lookup = parts[1] if len(parts) > 1 else "eq"
    field = "id" if field == "pk" else field
    operator = (
        constants.SQL_OPERATORS[lookup]
        if lookup in constants.SQL_OPERATORS
        else "="
    )

    return field, operator
