from __future__ import annotations

from collections.abc import Collection
from typing import (
    Any,
    Generic,
    Iterable,
    Literal,
    Mapping,
    Optional,
    Self,
    Sequence,
    TypeVar,
    Union,
)
from uuid import UUID

from bson.errors import InvalidId
from bson.objectid import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from py_cachify import lock
from pydantic import (
    BaseModel,
    GetCoreSchemaHandler,
    GetJsonSchemaHandler,
)
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, core_schema
from pydantic_core.core_schema import (
    ValidationInfo,
)
from pymongo import ReplaceOne, ReturnDocument, UpdateOne
from pymongo.results import BulkWriteResult

from ...errors import ConcurrencyError, NotExistsError
from ...infrastructure.db import Mongo, MongoCollection
from ...utils import Crypto, DateTime, Strings
from ...utils.objects import model_dump

DocumentType = TypeVar("DocumentType", bound=BaseModel)

VersionCheckResult = Literal["valid", "not exist", "version mismatch"]

ReplaceOneItem = tuple[Mapping[str, Any], Union[Mapping[str, Any], DocumentType]]


class MongoCommandsMixin(Generic[DocumentType]):
    @classmethod
    def get_collection_name(cls) -> str:
        return getattr(cls.Meta, "collection_name", None) or Strings.to_snake_case(  # noqa
            Strings.to_plural(cls.__name__)
        )

    @classmethod
    def is_pydantic_model(cls) -> bool:
        return issubclass(cls, BaseModel)

    @classmethod
    def replace_one(
        cls, match: Mapping[str, Any], replacement: Mapping[str, Any]
    ) -> Optional[Self]:
        with MongoCollection(name=cls.get_collection_name()) as collection:
            replaced: Optional[dict[str, Any]] = collection.find_one_and_replace(
                filter=match,
                replacement=replacement,
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
            if not replaced:
                return None
            replaced.setdefault(
                "id", str(replaced.get("_id", None) or replaced.get("id", None))
            )

            return cls.model_validate(replaced) if cls.is_pydantic_model() else replaced  # type: ignore

    @classmethod
    async def replace_one_async(
        cls,
        match: Mapping[str, Any],
        replacement: Union[Mapping[str, Any], DocumentType],
    ) -> Optional[Self]:
        async with MongoCollection(name=cls.get_collection_name()) as collection:
            replaced = await collection.find_one_and_replace(
                filter=match,
                replacement=model_dump(replacement),
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
            replaced["id"] = str(replaced.get("id", None) or replaced.get("_id", None))

            return cls.model_validate(replaced) if replaced else None

    @classmethod
    def replace_many(
        cls,
        requests: Iterable[ReplaceOneItem],
    ) -> BulkWriteResult:
        with MongoCollection(name=cls.get_collection_name()) as collection:
            return collection.bulk_write(
                requests=cls._create_bulk_replace(requests),
            )

    @classmethod
    async def replace_many_async(
        cls, requests: Iterable[ReplaceOneItem]
    ) -> BulkWriteResult:
        async with MongoCollection(name=cls.get_collection_name()) as collection:
            return await collection.bulk_write(
                requests=cls._create_bulk_replace(requests),
            )

    def save(self) -> None:
        _id = getattr(self, "id", None)
        created = (  # noqa
            self.update_one(_id, self) if _id is not None else self.create(self)
        )

        if created is not None:
            for key, value in vars(created).items():
                if isinstance(value, ObjectId):
                    value = DocumentID(str(value))
                setattr(self, key, value)

    async def save_async(self) -> None:
        _id = getattr(self, "id", None)
        created = (  # noqa
            await self.update_one_async(_id, self)
            if _id is not None
            else await self.create_async(self)
        )
        if created is not None:
            for key, value in vars(created).items():
                if isinstance(value, ObjectId):
                    value = DocumentID(str(value))
                setattr(self, key, value)

    @classmethod
    def create(cls, entity: DocumentType) -> Optional[Self]:
        if not entity:
            return None
        entity = cls.model_validate(entity)
        entity.before_insert()
        with Mongo() as db:
            collection = db.get_collection(name=cls.get_collection_name())
            _id = ObjectId()
            data = entity.model_dump(exclude={"id"})
            data.pop("_id", None)
            data.pop("id", None)
            created = collection.find_one_and_replace(
                filter={"_id": _id},
                replacement=data,
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
            created["id"] = str(
                created.get("id", None) or created.get("_id", None) or _id
            )

            return cls.model_validate(created) if created else None

    @classmethod
    async def create_async(cls, entity: DocumentType) -> Optional[Self]:
        if not entity:
            return None
        entity = cls.model_validate(entity)
        await entity.before_insert_async()
        async with Mongo() as db:
            collection = db.get_collection(name=cls.get_collection_name())
            _id = ObjectId()
            data = entity.model_dump(exclude={"id"})
            data.pop("_id", None)
            data.pop("id", None)
            created = await collection.find_one_and_replace(
                filter={"_id": _id},
                replacement=data,
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
            created["id"] = str(
                created.get("id", None) or created.get("_id", None) or _id
            )
            return cls.model_validate(created) if created else None

    @classmethod
    def update_one(
        cls, pk: Union[str, DocumentID, ObjectId], entity: DocumentType
    ) -> Optional[Self]:
        entity = cls.model_validate(entity)  # noqa

        data = entity.model_dump(exclude={"id"}, exclude_unset=True)
        _id = ObjectId(pk)

        if "updated_at" in cls.get_fields():
            data["updated_at"] = DateTime.now()
        data = {"$set": data}
        with MongoCollection(name=cls.get_collection_name()) as collection:
            if "version" in cls.get_fields():
                version = getattr(entity, "version", None) or 1
                version_check_result = cls.check_version(
                    pk=pk,
                    version=version,
                    collection=collection,  # type: ignore
                )
                if version_check_result == "not exist":
                    raise NotExistsError(cls.get_collection_name(), pk)
                elif version_check_result == "version mismatch":
                    raise ConcurrencyError(cls.get_collection_name(), pk)
                entity.before_update()
                data["$inc"] = {"version": 1}
                data["$set"].pop("version", None)
            updated = collection.find_one_and_update(
                filter={"_id": _id},
                update=data,
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
            return cls.model_validate(updated) if updated else None

    @classmethod
    def update_many(cls, operations: Sequence[UpdateOne]) -> BulkWriteResult:
        with MongoCollection(name=cls.get_collection_name()) as collection:
            return collection.bulk_write(operations)

    @classmethod
    async def update_many_async(
        cls, operations: Sequence[UpdateOne]
    ) -> BulkWriteResult:
        async with MongoCollection(name=cls.get_collection_name()) as collection:
            return await collection.bulk_write(operations)

    @classmethod
    def check_version(
        cls,
        *,
        pk: Union[str, DocumentID, ObjectId],
        version: int,
        collection: Optional[Collection[Mapping[str, Any]]] = None,
    ) -> VersionCheckResult:
        def _check_version(
            coll: Collection[Mapping[str, Any]],
        ) -> VersionCheckResult:
            with lock(f"mongo:{cls.get_collection_name()}:{pk}"):
                doc = coll.find_one({"_id": ObjectId(pk)})  # type: ignore
                if not doc:
                    return "not exist"
                return (
                    "valid" if doc.get("version", -1) == version else "version mismatch"
                )

        if collection is None:
            with Mongo() as db:
                collection = db.get_collection(name=cls.get_collection_name())
                return _check_version(collection)  # type: ignore
        return _check_version(collection)

    @classmethod
    async def check_version_async(
        cls,
        *,
        pk: Union[str, DocumentID, ObjectId],
        version: int,
        collection: Optional[AsyncIOMotorCollection[Mapping[str, Any]]] = None,
    ) -> VersionCheckResult:
        async def _check_version(
            _collection: AsyncIOMotorCollection,
        ) -> VersionCheckResult:
            async with lock(f"mongo:{cls.get_collection_name()}:{pk}"):
                doc = await _collection.find_one({"_id": ObjectId(pk)})
                if not doc:
                    return "not exist"
                return (
                    "valid" if doc.get("version", -1) == version else "version mismatch"
                )

        if collection is None:
            async with MongoCollection(name=cls.get_collection_name()) as collection:
                return await _check_version(collection)
        return await _check_version(collection)

    @classmethod
    async def update_one_async(
        cls, pk: Union[str, DocumentID, ObjectId], entity: DocumentType
    ) -> Optional[Self]:
        if not entity:
            return None
        entity = cls.model_validate(entity)  # noqa

        data = entity.model_dump(exclude={"id"}, exclude_unset=True)
        _id = ObjectId(pk)

        if "updated_at" in cls.get_fields():
            data["updated_at"] = DateTime.now()
        data = {"$set": data}
        async with MongoCollection(name=cls.get_collection_name()) as collection:
            if "version" in cls.get_fields():
                version = getattr(entity, "version", None) or 1
                version_check_result = await cls.check_version_async(
                    pk=pk, version=version, collection=collection
                )
                if version_check_result == "not exist":
                    raise NotExistsError(cls.get_collection_name(), pk)
                elif version_check_result == "version mismatch":
                    raise ConcurrencyError(cls.get_collection_name(), pk)
                await entity.before_update_async()
                data["$inc"] = {"version": 1}
                data["$set"].pop("version", None)
            updated = await collection.find_one_and_update(
                filter={"_id": _id},
                update=data,
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
            return cls.model_validate(updated) if updated else None

    @classmethod
    def delete(cls, pk: Union[str, DocumentID, ObjectId]) -> int:
        with MongoCollection(name=cls.get_collection_name()) as collection:
            result = collection.delete_one({"_id": ObjectId(pk)})

            return result.deleted_count if result else 0

    @classmethod
    def delete_all(cls) -> int:
        with MongoCollection(name=cls.get_collection_name()) as collection:
            result = collection.delete_many({})

            return result.deleted_count if result else 0

    @classmethod
    async def delete_async(cls, pk: Union[str, DocumentID, ObjectId]) -> int:
        async with MongoCollection(name=cls.get_collection_name()) as collection:
            result = await collection.delete_one({"_id": ObjectId(pk)})

            return result.deleted_count if result else 0

    @classmethod
    async def delete_all_async(cls) -> int:
        async with MongoCollection(name=cls.get_collection_name()) as collection:
            result = await collection.delete_many({})

            return result.deleted_count if result else 0

    @classmethod
    def delete_many(cls, **kwargs) -> int:
        from .queries import MongoQueriesMixin

        fltr = MongoQueriesMixin._build_filter(**kwargs)  # noqa
        with MongoCollection(name=cls.get_collection_name()) as collection:
            result = collection.delete_many(fltr)

            return result.deleted_count if result else 0

    @classmethod
    async def delete_many_async(cls, **kwargs) -> int:
        from .queries import MongoQueriesMixin

        fltr = MongoQueriesMixin._build_filter(**kwargs)  # noqa
        async with MongoCollection(name=cls.get_collection_name()) as collection:
            result = await collection.delete_many(fltr)

            return result.deleted_count if result else 0

    @classmethod
    def _create_bulk_replace(
        cls,
        requests: Iterable[ReplaceOneItem],
    ) -> list[ReplaceOne]:
        return [
            ReplaceOne(
                filter=match,
                replacement=model_dump(replacement),
                upsert=True,
            )
            for match, replacement in requests
        ]


plain_validator = (
    core_schema.with_info_plain_validator_function
    if hasattr(core_schema, "with_info_plain_validator_function")
    else core_schema.with_info_plain_validator_function
)


class DocumentID(ObjectId):
    """
    ObjectId field. Compatible with Pydantic.
    """

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, _: ValidationInfo):
        if isinstance(v, bytes):
            v = v.decode("utf-8")
        try:
            return cls(v)
        except (InvalidId, TypeError) as e:
            raise ValueError("Id must be of type PydanticObjectId") from e

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,  # noqa
        handler: GetCoreSchemaHandler,  # noqa
    ) -> CoreSchema:  # type: ignore
        return core_schema.json_or_python_schema(
            python_schema=plain_validator(cls.validate),
            json_schema=plain_validator(
                cls.validate,
                metadata={
                    "pydantic_js_input_core_schema": core_schema.str_schema(
                        pattern="^[0-9a-f]{24}$",
                        min_length=24,
                        max_length=24,
                    )
                },
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda instance: str(instance), when_used="json"
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(
        cls,
        schema: core_schema.CoreSchema,
        handler: GetJsonSchemaHandler,  # type: ignore
    ) -> JsonSchemaValue:
        json_schema = handler(schema)
        json_schema.update(
            type="string",
            example="5eb7cf5a86d9755df3a6c593",
        )
        return json_schema

    @staticmethod
    def from_uuid(id_: Union[UUID, str]) -> "DocumentID":
        return DocumentID(Crypto.to_object_id_str(id_))


def _create_document_id(value: Any) -> Optional[DocumentID]:
    if not value:
        return None
    if isinstance(value, DocumentID):
        return value
    if isinstance(value, ObjectId):
        return DocumentID(str(value))
    if isinstance(value, (bytes, bytearray, memoryview)):
        value = value.decode("utf-8")
    return DocumentID(str(value))
