from collections.abc import Collection
from typing import (
    Any,
    Literal,
    Mapping,
    Optional,
    TypeVar,
    Union,
)

from bson.objectid import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from py_cachify import lock
from pydantic import BaseModel
from pymongo import ReturnDocument

from ...errors import ConcurrencyError, NotExistsError
from ...infrastructure.db import Mongo
from ...utils import DateTime
from ..models import DocumentID

DocumentType = TypeVar("DocumentType", bound=BaseModel)

VersionCheckResult = Literal["valid", "not exist", "version mismatch"]


class MongoCommandsMixin:
    def save(self) -> None:
        created = self.create(self)

        if created is not None:
            for key, value in vars(created).items():
                if isinstance(value, ObjectId):
                    value = DocumentID(str(value))
                setattr(self, key, value)

    async def save_async(self) -> None:
        created = await self.create_async(self)
        if created is not None:
            for key, value in vars(created).items():
                if isinstance(value, ObjectId):
                    value = DocumentID(str(value))
                setattr(self, key, value)

    @classmethod
    def create(cls, entity: DocumentType) -> Optional[DocumentType]:
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
    async def create_async(cls, entity: DocumentType) -> Optional[DocumentType]:
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
    def update(
        cls, pk: Union[str, DocumentID, ObjectId], entity: DocumentType
    ) -> Optional[DocumentType]:
        entity = cls.model_validate(entity)

        data = entity.model_dump(exclude={"id"}, exclude_unset=True)
        _id = ObjectId(pk)

        if "updated_at" in cls.fields:
            data["updated_at"] = DateTime.now()
        data = {"$set": data}
        with Mongo() as db:
            collection = db.get_collection(name=cls.get_collection_name())
            if "version" in cls.fields:
                version = entity.version
                version_check_result = cls.check_version(
                    pk=pk, version=version, collection=collection
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
    def check_version(
        cls,
        *,
        pk: Union[str, DocumentID, ObjectId],
        version: int,
        collection: Optional[Collection[Mapping[str, Any]]] = None,
    ) -> VersionCheckResult:
        def _check_version(
            _collection: Collection,
        ) -> VersionCheckResult:
            with lock(f"mongo:{cls.get_collection_name()}:{pk}"):
                doc = _collection.find_one({"_id": ObjectId(pk)})
                if not doc:
                    return "not exist"
                return (
                    "valid" if doc.get("version", -1) == version else "version mismatch"
                )

        if collection is None:
            with Mongo() as db:
                collection = db.get_collection(name=cls.get_collection_name())
                return _check_version(collection)
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
            async with Mongo() as db:
                collection = db.get_collection(name=cls.get_collection_name())
                return await _check_version(collection)
        return await _check_version(collection)

    @classmethod
    async def update_async(
        cls, pk: Union[str, DocumentID, ObjectId], entity: DocumentType
    ) -> Optional[DocumentType]:
        if not entity:
            return None
        entity = cls.model_validate(entity)

        data = entity.model_dump(exclude={"id"}, exclude_unset=True)
        _id = ObjectId(pk)

        if "updated_at" in cls.fields:
            data["updated_at"] = DateTime.now()
        data = {"$set": data}
        async with Mongo() as db:
            collection = db.get_collection(name=cls.get_collection_name())
            if "version" in cls.fields:
                version = entity.version
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
        with Mongo() as db:
            collection = db.get_collection(name=cls.get_collection_name())
            result = collection.delete_one({"_id": ObjectId(pk)})

            return result.deleted_count if result else 0

    @classmethod
    def delete_all(cls) -> int:
        with Mongo() as db:
            collection = db.get_collection(name=cls.get_collection_name())
            result = collection.delete_many({})

            return result.deleted_count if result else 0

    @classmethod
    async def delete_async(cls, pk: Union[str, DocumentID, ObjectId]) -> int:
        async with Mongo() as db:
            collection = db.get_collection(name=cls.get_collection_name())
            result = await collection.delete_one({"_id": ObjectId(pk)})

            return result.deleted_count if result else 0

    @classmethod
    async def delete_all_async(cls) -> int:
        async with Mongo() as db:
            collection = db.get_collection(name=cls.get_collection_name())
            result = await collection.delete_many({})

            return result.deleted_count if result else 0
