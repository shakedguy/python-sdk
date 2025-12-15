from collections.abc import AsyncGenerator, Generator
from typing import (
    Any,
    Generic,
    Mapping,
    Optional,
    Self,
    Type,
    TypeVar,
)

from pydantic import BaseModel
from qdrant_client.models import FieldCondition, Filter, Match, MatchAny, MatchText

from ...infrastructure.db import Qdrant
from ...utils.strings import to_plural, to_snake_case
from ..base import FindAsyncResult, FindResult

DocumentType = TypeVar("DocumentType", bound=BaseModel)


class QdrantQueriesMixin(Generic[DocumentType]):

    @classmethod
    def get_collection_name(cls) -> str:
        return getattr(cls.Meta, "collection_name", None) or to_snake_case(  # noqa
            to_plural(cls.__name__)
        )

    @classmethod
    def find_by_pk(cls, pk: str) -> Optional[Self]:
        with Qdrant() as client:
            docs = client.query(
                collection_name=cls.get_collection_name(),
                query_text="",
                query_filter=Filter(must=FieldCondition(
                    key="id",
                    match=Match(MatchText(text=str(pk))),
                ),
                ),
                limit=1,
            )

            return cls.model_validate(docs[0]) if docs else None

    @classmethod
    async def find_by_pk_async(
            cls, pk: str
    ) -> Optional[Self]:
        async with Qdrant() as client:
            docs = await client.query(
                collection_name=cls.get_collection_name(),
                query_text="",
                query_filter=Filter(must=FieldCondition(
                    key="id",
                    match=Match(MatchText(text=str(pk))),
                ),
                ),
                limit=1,
            )

            return cls.model_validate(docs[0]) if docs else None

    @classmethod
    def find_one(cls, **kwargs: Any) -> Optional[Self]:
        fltr = cls._build_filter(**kwargs)
        with Qdrant() as client:
            docs = client.query(
                collection_name=cls.get_collection_name(),
                query_text="",
                query_filter=fltr,
                limit=1,
            )

            return cls.model_validate(docs[0]) if docs else None

    @classmethod
    async def find_one_async(cls, **kwargs: Any) -> Optional[Self]:
        fltr = cls._build_filter(**kwargs)
        async with Qdrant() as client:
            docs = await client.query(
                collection_name=cls.get_collection_name(),
                query_text="",
                query_filter=fltr,
                limit=1,
            )

            return cls.model_validate(docs[0]) if docs else None

    @classmethod
    def _find_gen(
            cls,
            *,
            limit: Optional[int] = None,
            **kwargs: Any,
    ) -> Generator[Type[Self], None, None]:
        fltr = cls._build_filter(**kwargs)
        with Qdrant() as client:

            for doc in client.query(
                    collection_name=cls.get_collection_name(),
                    query_text="",
                    query_filter=fltr,
                    limit=limit,
            ):
                if doc:
                    yield cls.model_validate(doc)

    @classmethod
    async def _find_gen_async(
            cls,
            *,
            limit: Optional[int] = None,
            **kwargs: Any,
    ) -> AsyncGenerator[Type[Self]]:
        fltr = cls._build_filter(**kwargs)
        async with Qdrant() as client:

            for doc in await client.query(
                    collection_name=cls.get_collection_name(),
                    query_text="",
                    query_filter=fltr,
                    limit=limit,
            ):
                if doc:
                    yield cls.model_validate(doc)

    @classmethod
    def find(
            cls,
            *,
            skip: Optional[int] = None,
            limit: Optional[int] = None,
            sort: Optional[Mapping[str, Any]] = None,
            **kwargs: Any,
    ) -> FindResult[Type[Self]]:
        return FindResult(
            lambda: cls._find_gen(skip=skip, limit=limit, sort=sort, **kwargs)
        )

    @classmethod
    def find_async(
            cls,
            *,
            skip: Optional[int] = None,
            limit: Optional[int] = None,
            sort: Optional[Mapping[str, Any]] = None,
            **kwargs: Any,
    ) -> FindAsyncResult[Type[Self]]:
        return FindAsyncResult(
            lambda: cls._find_gen_async(skip=skip, limit=limit, sort=sort, **kwargs)
        )

    @classmethod
    def count(cls, **kwargs: Any) -> int:
        fltr = cls._build_filter(**kwargs)
        with Qdrant() as client:
            return client.count(collection_name=cls.get_collection_name(), count_filter=fltr).count

    @classmethod
    async def count_async(cls, **kwargs: Any) -> int:
        fltr = cls._build_filter(**kwargs)
        async with Qdrant() as client:
            res = await client.count(collection_name=cls.get_collection_name(), count_filter=fltr)
            return res.count

    @classmethod
    def _parse_filter(cls, key: str, value: Any) -> tuple[str, FieldCondition]:
        parts = key.split("__")
        field = parts[0]
        lookup = parts[1] if len(parts) > 1 else "eq"
        field = "id" if field == "pk" else field
        if lookup == "eq":
            match = MatchText(text=str(value)) if isinstance(value, str) else MatchAny(any=value)
            return "must", FieldCondition(key=field, match=match)
        elif lookup == "ne":
            match = MatchText(text=str(value)) if isinstance(value, str) else MatchAny(any=value)
            return "must_not", FieldCondition(key=field, match=match)

        return "must", FieldCondition(
            key=field,
            match=MatchText(text=str(value)) if isinstance(value, str) else MatchAny(any=value)
        )

    @classmethod
    def _build_filter(cls, **kwargs: Any) -> Filter:
        conditions = [cls._parse_filter(key, value) for key, value in kwargs.items()]

        return Filter(
            must=[c[1] for c in conditions if c[0] == "must"],
            must_not=[c[1] for c in conditions if c[0] == "must_not"],
            should=[c[1] for c in conditions if c[0] == "should"],

        )
