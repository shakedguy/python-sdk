from __future__ import annotations

import asyncio
from collections.abc import Collection
from typing import override

from pydantic import (
    AliasChoices,
    Field,
    PositiveInt,
)

from ... import errors
from ...utils import DateTime
from ..models import BaseModel, DateTimeField, DocumentIDField
from .commands import MongoCommandsMixin
from .indexes import DocumentIndex, DocumentIndexType
from .queries import MongoQueriesMixin

VERSION_INDEX = DocumentIndex(
    name="idx_id_and_version",
    unique=True,
    fields={"_id": DocumentIndexType.ASCENDING, "version": DocumentIndexType.ASCENDING},
)


class DocumentModel(BaseModel, MongoQueriesMixin, MongoCommandsMixin):
    id: DocumentIDField = Field(
        default=None,
        title="Id",
        description="Document ID",
        validation_alias=AliasChoices("_id", "id"),
    )

    version: PositiveInt = Field(
        default=1,
        title="Version",
        description="The version of the record.",
        validation_alias=AliasChoices("version", "_version"),
    )

    class Meta:
        collection_name: str = ""
        indexes: Collection[DocumentIndex] = list()

    @classmethod
    def get_indexes(cls) -> Collection[DocumentIndex]:
        return (
            list()
            if cls.__name__ in ["DocumentTimeStampedModel"]
            else [VERSION_INDEX] + [idx for idx in getattr(cls.Meta, "indexes", [])]
        )

    def refresh_from_db(self) -> None:
        if self.id is None:
            raise errors.NoIdError(self.get_collection_name())
        from ...infrastructure.db import Mongo

        with Mongo() as db:
            record = db[self.get_collection_name()].find_one({"_id": self.id})
            if record is None:
                raise errors.NotExistsError(self.get_collection_name(), self.id)
        for k, v in record.items():
            setattr(self, k, v)

    async def refresh_from_db_async(self) -> None:
        if self.id is None:
            raise errors.NoIdError(self.get_collection_name())
        from ...infrastructure.db import Mongo

        async with Mongo() as db:
            record = await db[self.get_collection_name()].find_one({"_id": self.id})
            if record is None:
                raise errors.NotExistsError(self.get_collection_name(), self.id)
        for k, v in record.items():
            setattr(self, k, v)

    def before_update(self) -> None:
        self.version += 1

    def before_insert(self) -> None:
        self.version = 1
        self.id = None

    async def before_update_async(self) -> None:
        await asyncio.sleep(0)
        self.version += 1

    async def before_insert_async(self) -> None:
        await asyncio.sleep(0)
        self.version = 1
        self.id = None


class DocumentTimeStampedModel(DocumentModel):
    created_at: DateTimeField = Field(
        default=DateTime.now(),
        title="Created At",
        description="The date and time the record was created.",
    )
    updated_at: DateTimeField = Field(
        default=DateTime.now(),
        title="Updated At",
        description="The date and time the record was last updated.",
    )

    @override
    def before_update(self) -> None:
        super().before_update()
        self.updated_at = DateTime.now()

    @override
    def before_insert(self) -> None:
        super().before_insert()
        self.created_at = DateTime.now()

    @override
    async def before_update_async(self) -> None:
        await super().before_update_async()
        self.updated_at = DateTime.now()

    @override
    async def before_insert_async(self) -> None:
        await super().before_insert_async()
        self.created_at = DateTime.now()
