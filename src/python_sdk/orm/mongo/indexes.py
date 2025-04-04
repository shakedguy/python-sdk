from typing import Any, Mapping, Optional, Union

from pydantic import (
    Field,
)
from pymongo import ASCENDING, DESCENDING, GEO2D, GEOSPHERE, HASHED, TEXT

from src.python_sdk.orm.models.model import BaseModel
from src.python_sdk.utils import enums


class DocumentIndexType(enums.StrEnum):
    ASCENDING = "asc"
    DESCENDING = "desc"
    TEXT = "text"
    HASHED = "hashed"
    GEOSPHERE = "2dsphere"
    GEO2D = "2d"

    @property
    def pymongo_value(self) -> Union[int, str]:
        mapping = {
            DocumentIndexType.ASCENDING: ASCENDING,
            DocumentIndexType.DESCENDING: DESCENDING,
            DocumentIndexType.TEXT: TEXT,
            DocumentIndexType.HASHED: HASHED,
            DocumentIndexType.GEOSPHERE: GEOSPHERE,
            DocumentIndexType.GEO2D: GEO2D,
        }
        return mapping[self]


class DocumentIndex(BaseModel):
    name: str = Field(..., title="Name", description="The index name.")
    unique: Optional[bool] = Field(
        default=False, title="Unique", description="The index is unique."
    )
    background: Optional[bool] = Field(
        default=False,
        title="Background",
        description="Index is created in the background.",
    )
    fields: dict[str, DocumentIndexType] = Field(
        ..., title="Keys", description="The index keys."
    )

    @property
    def pymongo_keys(self) -> Mapping[str, Any]:
        return {k: v.pymongo_value for k, v in self.fields.items()}
