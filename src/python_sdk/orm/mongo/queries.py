from collections.abc import AsyncGenerator, Generator
from typing import (
    Any,
    Generic,
    Mapping,
    Optional,
    Self,
    Type,
    TypeVar,
    Union,
)

from bson.objectid import ObjectId
from pydantic import BaseModel

from ...conf import constants
from ...domain.base.fields import DocumentID
from ...infrastructure.db import Mongo, MongoCollection
from ...utils import Strings
from ..base import FindAsyncResult, FindResult

DocumentType = TypeVar("DocumentType", bound=BaseModel)


class MongoQueriesMixin(Generic[DocumentType]):
    @classmethod
    def get_collection_name(cls) -> str:
        return getattr(cls.Meta, "collection_name", None) or Strings.to_snake_case(  # noqa
            Strings.to_plural(cls.__name__)
        )

    @classmethod
    def find_by_pk(cls, pk: Union[str, DocumentID, ObjectId]) -> Optional[Self]:
        with MongoCollection(name=cls.get_collection_name()) as collection:
            doc = collection.find_one({"_id": ObjectId(pk)})

            return cls.model_validate(doc) if doc else None

    @classmethod
    async def find_by_pk_async(
        cls, pk: Union[str, DocumentID, ObjectId]
    ) -> Optional[Self]:
        async with MongoCollection(name=cls.get_collection_name()) as collection:
            entity = await collection.find_one({"_id": ObjectId(pk)})
            return cls.model_validate(entity) if entity else None

    @classmethod
    def find_one(cls, **kwargs: Any) -> Optional[Self]:
        fltr = cls._build_filter(**kwargs)
        with MongoCollection(name=cls.get_collection_name()) as collection:
            entity = collection.find_one(fltr)
            return cls.model_validate(entity) if entity else None

    @classmethod
    async def find_one_async(cls, **kwargs: Any) -> Optional[Self]:
        fltr = cls._build_filter(**kwargs)
        async with Mongo() as db:
            collection = db.get_collection(name=cls.get_collection_name())
            entity = await collection.find_one(fltr)
            return cls.model_validate(entity) if entity else None

    @classmethod
    def _find_gen(
        cls,
        *,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
        sort: Optional[Mapping[str, Any]] = None,
        **kwargs: Any,
    ) -> Generator[Type[Self], None, None]:
        fltr = cls._build_filter(**kwargs)
        with MongoCollection(name=cls.get_collection_name()) as collection:
            cursor = collection.find(fltr)
            if skip is not None:
                cursor = cursor.skip(skip)
            if limit is not None:
                cursor = cursor.limit(limit)
            if sort is not None:
                cursor = cursor.sort(sort)

            for doc in cursor:
                if doc:
                    yield cls.model_validate(doc)

    @classmethod
    async def _find_gen_async(
        cls,
        *,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
        sort: Optional[Mapping[str, Any]] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[Type[Self]]:
        fltr = cls._build_filter(**kwargs)
        async with MongoCollection(name=cls.get_collection_name()) as collection:
            cursor = collection.find(fltr)
            if skip is not None:
                cursor = cursor.skip(skip)
            if limit is not None:
                cursor = cursor.limit(limit)
            if sort is not None:
                cursor = cursor.sort(sort)

            async for doc in cursor:
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
        with MongoCollection(name=cls.get_collection_name()) as collection:
            return collection.count_documents(filter=fltr)

    @classmethod
    async def count_async(cls, **kwargs: Any) -> int:
        fltr = cls._build_filter(**kwargs)
        async with MongoCollection(name=cls.get_collection_name()) as collection:
            return await collection.count_documents(filter=fltr)

    @classmethod
    def exists(cls, **kwargs: Any) -> bool:
        fltr = cls._build_filter(**kwargs)
        with MongoCollection(name=cls.get_collection_name()) as collection:
            return collection.find_one(fltr) is not None

    @classmethod
    async def exists_async(cls, **kwargs: Any) -> bool:
        fltr = cls._build_filter(**kwargs)
        async with MongoCollection(name=cls.get_collection_name()) as collection:
            return (await collection.find_one(fltr)) is not None

    @classmethod
    def _parse_filter(cls, key: str) -> tuple[str, str]:
        field, lookup = (key.split("__") + ["eq"])[:2]
        field = "id" if field == "pk" else field
        operator = constants.MONGO_OPERATORS.get(lookup, "$eq")
        return field, operator

    @classmethod
    def _build_filter(cls, **kwargs: Any) -> dict[str, Any]:
        res = {
            cls._parse_filter(key)[0]: {cls._parse_filter(key)[1]: value}
            for key, value in kwargs.items()
        }

        return (
            {"$and": [{key: value} for key, value in res.items()]}
            if len(res.keys()) > 1
            else res
        )
