from __future__ import annotations

import asyncio
from collections.abc import Collection
from typing import Any, Mapping, Optional, Type, Union, cast, override

from loguru import logger
from pydantic import (
    AliasChoices,
    Field,
    PositiveInt,
)
from pymongo import ASCENDING, DESCENDING, GEO2D, GEOSPHERE, HASHED, TEXT

from ... import errors
from ...domain.base.base_model import BaseModel
from ...domain.base.fields import DateTimeField, DocumentIDField
from ...infrastructure.db import Mongo, MongoCollection
from ...orm.mongo.commands import MongoCommandsMixin
from ...orm.mongo.queries import MongoQueriesMixin
from ...utils import DateTime, Strings, enums, find_subclasses


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


class Document(BaseDocument, MongoQueriesMixin, MongoCommandsMixin):
    id: DocumentIDField = Field(
        default=None,
        title="Id",
        description="Document ID",
        validation_alias=AliasChoices("_id", "id"),
    )

    @staticmethod
    def get_all_documents() -> Collection[Type[Document]]:
        all_models = find_subclasses(Document)

        exclude = [
            Document,
            DocumentVersionModel,
            DocumentTimeStampedModel,
            DocumentTimeStampedVersionedModel,
        ]
        return [m for m in all_models if issubclass(m, Document) and m not in exclude]

    @classmethod
    def get_indexes(cls) -> Collection[DocumentIndex]:
        return getattr(cls.Meta, "indexes", list())

    @property
    def pk(self) -> Optional[str]:
        return str(self.id) if self.id else None

    def before_update(self) -> None:
        pass

    def before_insert(self) -> None:
        self.id = None

    async def before_update_async(self) -> None:
        pass

    async def before_insert_async(self) -> None:
        await asyncio.sleep(0)
        self.id = None

    def refresh_from_db(self) -> None:
        if self.id is None:
            raise errors.NoIdError(self.get_collection_name())

        record = self.find_by_pk(self.id)
        for k, v in record.items():
            setattr(self, k, v)

    async def refresh_from_db_async(self) -> None:
        if self.id is None:
            raise errors.NoIdError(self.get_collection_name())
        record = await self.find_by_pk_async(self.id)
        for k, v in record.items():
            setattr(self, k, v)

    @classmethod
    async def create_indexes_async(cls) -> None:
        logger.debug("Creating indexes")
        indexes = cls.get_indexes()
        if not len(indexes or []):
            return

        async with MongoCollection(cls.get_collection_name()) as coll:
            await asyncio.gather(
                *[
                    coll.create_index(
                        name=index.name,
                        keys=index.pymongo_keys,
                        unique=index.unique,
                        background=index.background,
                    )
                    for index in indexes
                ]
            )

    @classmethod
    def create_indexes(cls) -> None:
        indexes = cls.get_indexes()
        if not len(indexes or []):
            return
        with MongoCollection(cls.get_collection_name()) as coll:
            for index in indexes:
                coll.create_index(
                    name=index.name,
                    keys=index.pymongo_keys,
                    unique=index.unique,
                    background=index.background,
                )


class DocumentVersionModel(Document):
    version: PositiveInt = Field(
        default=1,
        title="Version",
        description="The version of the record.",
        validation_alias=AliasChoices("version", "_version", "v", "__v"),
    )

    def before_update(self) -> None:
        super().before_update()
        self.version += 1

    def before_insert(self) -> None:
        super().before_insert()
        self.version = 1

    async def before_update_async(self) -> None:
        await super().before_update_async()
        self.version += 1

    async def before_insert_async(self) -> None:
        await super().before_insert_async()
        self.version = 1

    @classmethod
    def get_indexes(cls) -> Collection[DocumentIndex]:
        return list(super().get_indexes()) + [VERSION_INDEX]


class DocumentTimeStampedModel(Document):
    created_at: DateTimeField = Field(
        default_factory=DateTime.now,
        title="Created At",
        description="The date and time the record was created.",
    )
    updated_at: DateTimeField = Field(
        default_factory=DateTime.now,
        title="Updated At",
        description="The date and time the record was last updated.",
    )

    @override  # noqa
    def before_update(self) -> None:
        super().before_update()
        self.updated_at = DateTime.now()

    @override  # noqa
    def before_insert(self) -> None:
        super().before_insert()
        self.created_at = DateTime.now()

    @override  # noqa
    async def before_update_async(self) -> None:
        await super().before_update_async()
        self.updated_at = DateTime.now()

    @override  # noqa
    async def before_insert_async(self) -> None:
        await super().before_insert_async()
        self.created_at = DateTime.now()


class DocumentTimeStampedVersionedModel(DocumentVersionModel, DocumentTimeStampedModel):
    pass


class MongoView(MongoQueriesMixin):
    class Meta:
        collection_name: str = ""
        source: str = ""
        pipeline: Collection[dict[str, str]] = list()

    @staticmethod
    def get_all_views() -> Collection[Type[MongoView]]:
        return find_subclasses(MongoView)

    @classmethod
    def get_pipeline(cls) -> Collection[dict[str, str]]:
        return getattr(cls.Meta, "pipeline", None) or []

    @classmethod
    def get_source(cls) -> str:
        return getattr(cls.Meta, "source", None) or ""

    @classmethod
    async def create_async(cls) -> None:
        collection_name, source, pipline = cls._build_create()

        async with Mongo() as db:
            await db.command(
                {
                    "create": collection_name,
                    "viewOn": source,
                    "pipeline": pipline,
                }
            )

    @classmethod
    def create(cls) -> None:
        collection_name, source, pipline = cls._build_create()

        with Mongo() as db:
            db.command(
                {
                    "create": collection_name,
                    "viewOn": source,
                    "pipeline": pipline,
                }
            )

    @classmethod
    def _build_create(cls) -> tuple[str, str, Collection[dict[str, str]]]:
        pipline = cls.get_pipeline()
        collection_name = cls.get_collection_name()
        source = cls.get_source()
        if not len(pipline or []):
            raise RuntimeError(f"Pipeline is not set for mongo view {cls.__name__}")
        if not collection_name:
            raise RuntimeError(
                f"Collection name is not set for mongo view {cls.__name__}"
            )
        if not source:
            raise RuntimeError(f"Source is not set for mongo view {cls.__name__}")

        return collection_name, source, pipline
