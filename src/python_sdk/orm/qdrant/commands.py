from __future__ import annotations

from typing import (
    Any,
    Generic,
    Literal,
    Mapping,
    Optional,
    Self,
    TypeVar,
    Union,
)

from pydantic import (
    BaseModel,
)
from qdrant_client.models import PointStruct

from ...infrastructure.db import Qdrant
from ...utils import Crypto, Strings

DocumentType = TypeVar("DocumentType", bound=BaseModel)

VersionCheckResult = Literal["valid", "not exist", "version mismatch"]

ReplaceOneItem = tuple[Mapping[str, Any], Union[Mapping[str, Any], DocumentType]]


class QdrantCommandsMixin(Generic[DocumentType]):
    @classmethod
    def get_collection_name(cls) -> str:
        return getattr(cls.Meta, "collection_name", None) or Strings.to_snake_case(  # noqa
            Strings.to_plural(cls.__name__)
        )

    @classmethod
    def is_pydantic_model(cls) -> bool:
        return issubclass(cls, BaseModel)

    @classmethod
    def create(cls, entity: DocumentType) -> Optional[Self]:
        if not entity:
            return None
        entity = cls.model_validate(entity)
        entity.before_insert()
        with Qdrant() as client:
            _id = Crypto.uuid7()
            data = entity.model_dump(mode="json", exclude={"id"})
            data.pop("_id", None)
            data["id"] = str(_id)
            vector = data.pop("embedding", None)
            client.upsert(
                collection_name=cls.get_collection_name(),
                points=[
                    PointStruct(
                        id=_id,
                        vector=vector,
                        payload=data,
                    )
                ]

            )
            entity.id = _id
            return entity

    @classmethod
    async def create_async(cls, entity: DocumentType) -> Optional[Self]:
        if not entity:
            return None
        entity = cls.model_validate(entity)
        await entity.before_insert_async()
        async with Qdrant() as client:
            _id = Crypto.uuid7()
            data = entity.model_dump(mode="json", exclude={"id"})
            data.pop("_id", None)
            data["id"] = str(_id)
            vector = data.pop("embedding", None)
            await client.upsert(
                collection_name=cls.get_collection_name(),
                points=[
                    PointStruct(
                        id=_id,
                        vector=vector,
                        payload=data,
                    )
                ]

            )
            entity.id = _id
            return entity
