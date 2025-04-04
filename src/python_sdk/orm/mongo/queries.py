from collections.abc import AsyncGenerator, AsyncIterator, Generator, Iterator
from typing import (
    Any,
    Callable,
    Generic,
    Literal,
    Optional,
    Type,
    TypeVar,
    Union,
)

from bson.objectid import ObjectId
from pydantic import BaseModel

from ...conf import constants
from ...infrastructure.db import Mongo
from ...utils import Strings
from ..models import DocumentID

DocumentType = TypeVar("DocumentType", bound=BaseModel)

VersionCheckResult = Literal["valid", "not exist", "version mismatch"]


class FindAsyncResult(Generic[DocumentType]):
    def __init__(
        self, generator_func: Callable[[], AsyncGenerator[Type[DocumentType]]]
    ):
        self._generator_func = generator_func

    def __aiter__(self) -> AsyncIterator[Type[DocumentType]]:
        return self._generator_func()

    async def to_list(self) -> list[Type[DocumentType]]:
        return [item async for item in self._generator_func()]


class FindResult(Generic[DocumentType]):
    def __init__(self, generator_func: Callable[[], Generator[Type[DocumentType]]]):
        self._generator_func = generator_func

    def __iter__(self) -> Iterator[Type[DocumentType]]:
        return self._generator_func()

    def to_list(self) -> list[Type[DocumentType]]:
        return [item for item in self._generator_func()]


class MongoQueriesMixin:
    @classmethod
    def get_collection_name(cls) -> str:
        return getattr(cls.Meta, "collection_name", None) or Strings.to_snake_case(
            Strings.to_plural(cls.__name__)
        )

    @classmethod
    def find_by_pk(cls, pk: Union[str, DocumentID, ObjectId]) -> Optional[DocumentType]:
        with Mongo() as db:
            collection = db.get_collection(name=cls.get_collection_name())
            doc = collection.find_one({"_id": ObjectId(pk)})

            return cls.model_validate(doc) if doc else None

    @classmethod
    async def find_by_pk_async(
        cls, pk: Union[str, DocumentID, ObjectId]
    ) -> Optional[DocumentType]:
        async with Mongo() as db:
            collection = db.get_collection(name=cls.get_collection_name())
            entity = await collection.find_one({"_id": ObjectId(pk)})
            return cls.model_validate(entity) if entity else None

    @classmethod
    def find_one(cls, **kwargs: Any) -> Optional[DocumentType]:
        fltr = cls._build_filter(**kwargs)
        with Mongo() as db:
            collection = db.get_collection(name=cls.get_collection_name())
            entity = collection.find_one(fltr)
            return cls.model_validate(entity) if entity else None

    @classmethod
    async def find_one_async(cls, **kwargs: Any) -> Optional[DocumentType]:
        fltr = cls._build_filter(**kwargs)
        async with Mongo() as db:
            collection = db.get_collection(name=cls.get_collection_name())
            entity = await collection.find_one(fltr)
            return cls.model_validate(entity) if entity else None

    @classmethod
    def _find_gen(cls, **kwargs: Any) -> Generator[Type[DocumentType]]:
        fltr = cls._build_filter(**kwargs)
        with Mongo() as db:
            collection = db.get_collection(name=cls.get_collection_name())

            for doc in collection.find(fltr):
                if doc:
                    yield cls.model_validate(doc)

    @classmethod
    def find(cls, **kwargs: Any) -> FindResult[Type[DocumentType]]:
        return FindResult(lambda: cls._find_gen(**kwargs))

    @classmethod
    async def _find_async_gen(cls, **kwargs: Any) -> AsyncGenerator[Type[DocumentType]]:
        fltr = cls._build_filter(**kwargs)
        async with Mongo() as db:
            collection = db.get_collection(name=cls.get_collection_name())

            async for doc in collection.find(fltr):
                if doc:
                    yield cls.model_validate(doc)

    @classmethod
    def find_async(cls, **kwargs: Any) -> FindAsyncResult[Type[DocumentType]]:
        return FindAsyncResult(lambda: cls._find_async_gen(**kwargs))

    @classmethod
    def count(cls, **kwargs: Any) -> int:
        fltr = cls._build_filter(**kwargs)
        with Mongo() as db:
            collection = db.get_collection(name=cls.get_collection_name())
            return collection.count_documents(filter=fltr)

    @classmethod
    async def count_async(cls, **kwargs: Any) -> int:
        fltr = cls._build_filter(**kwargs)
        async with Mongo() as db:
            collection = db.get_collection(name=cls.get_collection_name())
            return await collection.count_documents(filter=fltr)

    @classmethod
    def exists(cls, **kwargs: Any) -> bool:
        fltr = cls._build_filter(**kwargs)
        with Mongo() as db:
            collection = db.get_collection(name=cls.get_collection_name())
            return collection.find_one(fltr) is not None

    @classmethod
    async def exists_async(cls, **kwargs: Any) -> bool:
        fltr = cls._build_filter(**kwargs)
        async with Mongo() as db:
            collection = db.get_collection(name=cls.get_collection_name())
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
