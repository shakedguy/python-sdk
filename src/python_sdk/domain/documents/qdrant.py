from __future__ import annotations

import asyncio
from collections.abc import Collection
from datetime import datetime
from functools import cached_property
from typing import Callable, Optional, Sequence, Type, Union, override

from loguru import logger
from ollama import AsyncClient, Client
from pydantic import (
    AliasChoices,
    Field,
)
from qdrant_client.models import Distance, VectorParams

from ... import errors
from ...conf import settings
from ...domain.base.fields import DateTimeField, UUIDField
from ...infrastructure.db import Qdrant
from ...orm.qdrant import QdrantCommandsMixin, QdrantQueriesMixin
from ...utils import Crypto, DateTime, find_subclasses
from ._documents import BaseDocument, DocumentIndex


class QdrantDocument(BaseDocument, QdrantQueriesMixin, QdrantCommandsMixin):
    class Meta:
        collection_name: str = ""
        embedding_model: str = "nomic-embed-text"
        indexes: Collection[DocumentIndex] = list()
        text_formatter: Union[str, Callable[[QdrantDocument], str]]

    id: Optional[UUIDField] = Field(
        default=None,
        title="Id",
        description="Document ID",
        validation_alias=AliasChoices("_id", "id"),
    )

    text: str = Field(
        default_factory=str,
        title="Text",
        description="The text content of the document.",
        validation_alias=AliasChoices("text", "content", "body", "description", "content_text")
    )

    embedding: Optional[Union[Sequence[float], Sequence[Sequence[float]]]] = Field(
        default_factory=list,
        title="Embedding",
        description="The vector embedding of the document.",
        validation_alias=AliasChoices("embedding", "vector", "embeddings", "vectors"),
    )

    @property
    def pk(self) -> Optional[str]:
        return str(self.id) if self.id else None

    @cached_property
    def created_at(self) -> Optional[datetime]:
        return Crypto.uuid7_to_datetime(self.id) if self.id else None

    @staticmethod
    def get_all_documents() -> Collection[Type[QdrantDocument]]:
        all_models = find_subclasses(QdrantDocument)

        exclude = [
            QdrantDocument,
            QdrantTimeStampedDocument,
        ]
        return [m for m in all_models if issubclass(m, QdrantDocument) and m not in exclude]

    @classmethod
    def get_indexes(cls) -> Collection[DocumentIndex]:
        return getattr(cls.Meta, "indexes", list())

    @classmethod
    def _get_text_formatter(cls) -> Union[str, Callable[[QdrantDocument], str]]:
        return (
                getattr(cls.Meta, "text_formatter", None)
                or
                f"{cls.__name__.title()}({", ".join(f"{field}={{{field}}}" for field in cls.get_fields())})"
        )

    @classmethod
    def _get_embedding_model(cls) -> str:
        return getattr(cls.Meta, "embedding_model", "nomic-embed-text")

    def _create_text(self) -> None:
        formatter = self._get_text_formatter()

        self.text = formatter.format(**self.model_dump()) if isinstance(formatter, str) else formatter(self)

    def _create_embedding(self) -> None:
        self._create_text()
        embedding = Client().embed(
            model=self._get_embedding_model(),
            input=self.text,
        ).embeddings

        self.embedding = embedding[0] if len(embedding) == 1 else embedding

    async def _create_embedding_async(self) -> None:
        self._create_text()
        async with AsyncClient() as client:
            response = await client.embed(
                model=self._get_embedding_model(),
                input=self.text,
            )
            embedding = response.embeddings
            self.embedding = embedding[0] if len(embedding) == 1 else embedding

    def before_update(self) -> None:
        self._create_embedding()

    def before_insert(self) -> None:
        self.id = None
        self._create_embedding()

    async def before_update_async(self) -> None:
        await self._create_embedding_async()

    async def before_insert_async(self) -> None:
        self.id = None
        await self._create_embedding_async()

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

        collection_name = cls.get_collection_name()
        async with Qdrant() as client:
            await asyncio.gather(
                *[
                    client.create_payload_index(
                        collection_name=collection_name,
                        field_name=index.field,
                        wait=False,
                    )
                    for index in indexes if index.field is not None
                ]
            )

    @classmethod
    def create_indexes(cls) -> None:
        indexes = cls.get_indexes()
        if not len(indexes or []):
            return
        collection_name = cls.get_collection_name()
        with Qdrant() as client:
            for index in indexes:
                if index.field is not None:
                    client.create_payload_index(
                        collection_name=collection_name,
                        field_name=index.field,
                    )

    @classmethod
    def create_collection(cls) -> None:

        collection_name = cls.get_collection_name()
        with Qdrant() as client:
            if not client.collection_exists(collection_name):
                client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=settings.qdrant.default_vector_size,
                        distance=Distance.COSINE,
                    ),
                )
                cls.create_indexes()

    @classmethod
    async def create_collection_async(cls) -> None:

        collection_name = cls.get_collection_name()
        async with Qdrant() as client:
            if not await client.collection_exists(collection_name):
                await client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=settings.qdrant.default_vector_size,
                        distance=Distance.COSINE,
                    ),
                )
                await cls.create_indexes_async()


class QdrantTimeStampedDocument(QdrantDocument):
    updated_at: Optional[DateTimeField] = Field(
        default_factory=DateTime.now,
        title="Updated At",
        description="The date and time the record was last updated.",
    )

    @override  # noqa
    def before_insert(self) -> None:
        super().before_insert()

    @override  # noqa
    async def before_insert_async(self) -> None:
        await super().before_insert_async()

    @override  # noqa
    def before_update(self) -> None:
        super().before_update()
        self.updated_at = DateTime.utc_now()

    @override  # noqa
    async def before_update_async(self) -> None:
        await super().before_update_async()
        self.updated_at = DateTime.utc_now()
