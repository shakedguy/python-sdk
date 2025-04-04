import copy
import re
from typing import Any, Union

from jinja2 import Template

from ..conf import constants
from .datetime import DateTime
from .objects import ChangeKeysCase


def render_template(template: str, **kwargs) -> str:
    """
    Renders a template string with the given data.

    Args:
        template (str): The template string to render.
        **kwargs: The data to render the template with.

    Returns:
        str: The rendered template string.
    """

    result = template[:]
    data = ChangeKeysCase.flatten_all_cases(kwargs)

    dt_format = (
        re.search(r"date\((.*?)\)", template).group(1)
        if "date(" in template
        else "DD-MM-YYYY"
    )
    date_patterns = [
        r"\$\{date\(%s\)\}",
        r"\$\{\{date\(%s\)\}\}",
        r"\{date\(%s\)\}",
        r"\{\{date\(%s\)\}\}",
    ]
    now = DateTime.now().strftime(constants.DATETIME_JS_TO_PY.get(dt_format, dt_format))
    for pattern in date_patterns:
        result = re.sub(pattern % dt_format, now, result)

    for pattern in constants.VALID_VARIABLES_PATTERNS:
        result = re.sub(
            pattern,
            lambda m: str(get_value_from_path(data, m.group(1))),
            result,
        )

    result = re.sub(
        r"\$\{([a-zA-Z0-9_.\[\]]+)}",
        lambda m: str(get_value_from_path(data, m.group(1))),
        result,
    )

    return Template(result).render(**data)


def get_value_from_path(input_data: dict[str, Any], path: str) -> Any:
    keys = re.sub(r"\[(\d+)]", r".\1", path).split(".")
    keys = [k for k in keys if len(str(k).strip())]
    current: Union[dict[str, Any], list[Any]] = copy.deepcopy(input_data)

    for key in keys:
        if isinstance(current, dict):
            found_key = next(
                (k for k in current.keys() if str(k).lower() == str(key).lower()), None
            )
            current = current.get(found_key) if found_key is not None else None
        elif isinstance(current, list) and key.isdigit():
            current = current[int(key)]
        else:
            return None
    return current
