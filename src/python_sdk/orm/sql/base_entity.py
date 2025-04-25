from typing import cast

from pydantic import Field

from ...utils import Strings
from ..models.base_model import BaseModel
from ..models.fields import EntityIDField


class BaseEntity(BaseModel):
    id: EntityIDField = Field(
        default=None, title="Id", description="The primary key of the table."
    )

    @classmethod
    def get_columns(cls) -> set[str]:
        return set(sorted((cast(dict, cls.model_fields)).keys()))

    @classmethod
    def get_table_name(cls) -> str:
        return getattr(
            cls,
            "__tablename__",
            Strings.to_snake_case(Strings.to_plural(cls.__name__)),
        )
