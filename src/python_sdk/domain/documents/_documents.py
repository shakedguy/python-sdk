from __future__ import annotations

from collections.abc import Collection
from typing import Any, Mapping, Optional, Union, cast

from pydantic import (
    Field,
)
from pymongo import ASCENDING, DESCENDING, GEO2D, GEOSPHERE, HASHED, TEXT

from ...domain.base.base_model import BaseModel
from ...utils import Strings, enums


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
    fields: Optional[dict[str, DocumentIndexType]]  = Field(
        default=None, title="Keys", description="The index keys."
    )
    field:Optional[str] = Field(
        default=None,
        title="Field",
        description="The field to index. Use this if the index is on a single field.",
    )

    @property
    def field_names(self) -> Mapping[str, Any]:
        return {k: v.pymongo_value for k, v in self.fields.items()}


class BaseDocument(BaseModel):
    class Meta:
        collection_name: str = ""
        indexes: Collection[DocumentIndex] = list()

    @classmethod
    def get_collection_name(cls) -> str:
        return getattr(cls.Meta, "collection_name", None) or Strings.to_snake_case(
            Strings.to_plural(cls.__name__)
        )

    @classmethod
    def get_fields(cls) -> set[str]:
        return set(sorted((cast(dict, cls.model_fields)).keys()))

    def before_update(self) -> None: ...

    def before_insert(self) -> None: ...

    async def before_update_async(self) -> None: ...

    async def before_insert_async(self) -> None: ...


VERSION_INDEX = DocumentIndex(
    name="idx_id_and_version",
    unique=True,
    fields={"_id": DocumentIndexType.ASCENDING, "version": DocumentIndexType.ASCENDING},
)


