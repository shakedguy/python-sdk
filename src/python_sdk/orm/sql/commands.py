from typing import Any, Generic, Literal, Optional, Self, TypeVar, Union

from bson.objectid import ObjectId
from pydantic import BaseModel

from ...infrastructure.db import Postgres
from ...utils import DateTime
from ..mongo.commands import DocumentID

EntityType = TypeVar("EntityType", bound=BaseModel)


class SQLCommandsMixin(Generic[EntityType]):  # noqa
    """
    Mixin class providing SQL command functionalities for entities.
    """

    def save(self) -> None:
        """
        Save the current instance to the database.
        """
        if self.id is None:
            created = self.create(self)
            self._update_instance_attributes(created)
        else:
            self.update(self.id, self)


    async def save_async(self) -> None:
        """
        Asynchronously save the current instance to the database.
        """
        if self.id is None:
            created = self.create_async(self)
            self._update_instance_attributes(created)
        else:
            await self.update_async(self.id, self)

    @classmethod
    def create(cls, entity: EntityType) -> Optional[Self]:
        """
        Create a new record in the database.
        """
        if not entity:
            return None
        sql, params = cls._build_create(entity)
        return cls._execute_sync_query(sql, params)

    @classmethod
    async def create_async(cls, entity: EntityType) -> Optional[Self]:
        """
        Asynchronously create a new record in the database.
        """
        if not entity:
            return None
        sql, params = cls._build_create(entity, placeholder="index")
        return await cls._execute_async_query(sql, params)

    @classmethod
    def update(cls, pk: Union[int, str], entity: EntityType) -> Optional[Self]:
        """
        Update an existing record in the database.
        """
        if not entity:
            return None
        sql, params = cls._build_update(pk, entity)
        return cls._execute_sync_query(sql, params)

    @classmethod
    async def update_async(
        cls, pk: Union[int, str], entity: EntityType
    ) -> Optional[EntityType]:
        """
        Asynchronously update an existing record in the database.
        """
        if not entity:
            return None
        sql, params = cls._build_update(pk, entity, placeholder="index")
        return await cls._execute_async_query(sql, params)

    @classmethod
    def delete(cls, pk: Union[str, int]) -> int:
        """
        Delete a record from the database by primary key.
        """
        sql = cls._build_delete(pk)
        return cls._execute_sync_query(sql).rowcount

    @classmethod
    async def delete_async(cls, pk: Union[str, int]) -> int:
        """
        Asynchronously delete a record from the database by primary key.
        """
        sql = cls._build_delete(pk)
        result = await cls._execute_async_query(sql)
        return int(result.rowcount)

    @classmethod
    def _build_create(
        cls,
        entity: EntityType,
        placeholder: Optional[Literal["index", "string"]] = None,
    ) -> tuple[str, Any]:
        """
        Build the SQL query for creating a new record.
        """
        entity.before_insert()
        columns = list(entity.get_columns())



        if isinstance(entity.id, str) and len(entity.id) > 0:
            columns = ["id"] + columns

        params = cls._parse_values(
            **entity.model_dump(include=columns), cast_json=placeholder != "index"
        )
        values = ", ".join(
            [
                f"${idx + 1}" if placeholder == "index" else f"%({col})s"
                for idx, col in enumerate(columns)
            ]
        )
        values_names = ", ".join(columns)
        sql = f"INSERT INTO {entity.get_table_name()} ({values_names}) VALUES ({values}) RETURNING *"
        return sql, [
            params.get(col) for col in columns
        ] if placeholder == "index" else params

    @classmethod
    def _build_update(
        cls,
        pk: Union[int, str],
        entity: EntityType,
        placeholder: Optional[Literal["index", "string"]] = None,
    ) -> tuple[str, Any]:
        """
        Build the SQL query for updating an existing record.
        """
        entity.before_update()
        pk = cls._validate_pk(pk)
        params = cls._parse_values(
            **entity.model_dump(
                exclude={"id", "account", "inboxes"},
                exclude_unset=True,
                exclude_defaults=True,
            )
        )
        if "updated_at" in cls.get_columns():
            params["updated_at"] = DateTime.now()
        columns = sorted(params.keys())
        values = ", ".join(
            [
                f"{col} = ${idx + 1}"
                if placeholder == "index"
                else f"{col} = %({col})s"
                for idx, col in enumerate(columns)
            ]
        )

        pk_value = pk if isinstance(pk, int) else f"'{pk}'"
        sql = f"UPDATE {cls.get_table_name()} SET {values} WHERE id = {pk_value} RETURNING *"
        return sql, [
            params.get(col) for col in columns
        ] if placeholder == "index" else params

    @classmethod
    def _build_delete(cls, pk: Union[str, int]) -> str:
        """
        Build the SQL query for deleting a record by primary key.
        """
        pk = cls._validate_pk(pk)
        return f"DELETE FROM {cls.get_table_name()} WHERE id = {pk}"

    @classmethod
    def _validate_pk(cls, pk: Union[int, str]) -> Union[int, str]:
        """
        Validate the primary key to ensure it is a positive integer.
        """
        if not pk or str(pk) == "":
            raise ValueError("ID cannot be empty or None.")
        return int(pk) if str(pk).isdigit() else pk

    @classmethod
    def _update_instance_attributes(cls, created: Any) -> None:
        """
        Update the instance attributes with the values from the created record.
        """
        for key, value in vars(created).items():
            if isinstance(value, ObjectId):
                value = DocumentID(str(value))
            setattr(cls, key, value)

    @classmethod
    def _execute_sync_query(cls, sql: str, params: Any = None) -> Any:
        """
        Execute a synchronous SQL query.
        """
        with Postgres() as db:
            return db.execute(query=sql, params=params).fetchone()

    @classmethod
    async def _execute_async_query(cls, sql: str, params: Any = None) -> Any:
        """
        Execute an asynchronous SQL query.
        """
        async with Postgres() as db:
            return await db.fetchrow(sql, *params)
