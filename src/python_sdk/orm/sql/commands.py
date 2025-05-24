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
        created = self.update(self.id, self) if self.id else self.create(self)
        if created:
            self._update_instance_attributes(created)

    async def save_async(self) -> None:
        """
        Asynchronously save the current instance to the database.
        """
        created = await (
            self.update_async(self.id, self) if self.id else self.create_async(self)
        )
        if created:
            self._update_instance_attributes(created)

    def create(self, entity: EntityType) -> Optional[Self]:
        """
        Create a new record in the database.
        """
        if not entity:
            return None
        sql, params = self._build_create(entity)
        return self._execute_sync_query(sql, params)

    async def create_async(self, entity: EntityType) -> Optional[Self]:
        """
        Asynchronously create a new record in the database.
        """
        if not entity:
            return None
        sql, params = self._build_create(entity, placeholder="index")
        return await self._execute_async_query(sql, params)

    def update(self, pk: Union[int, str], entity: EntityType) -> Optional[Self]:
        """
        Update an existing record in the database.
        """
        if not entity:
            return None
        sql, params = self._build_update(pk, entity)
        return self._execute_sync_query(sql, params)

    async def update_async(
        self, pk: Union[int, str], entity: EntityType
    ) -> Optional[EntityType]:
        """
        Asynchronously update an existing record in the database.
        """
        if not entity:
            return None
        sql, params = self._build_update(pk, entity, placeholder="index")
        return await self._execute_async_query(sql, params)

    def delete(self, pk: Union[str, int]) -> int:
        """
        Delete a record from the database by primary key.
        """
        sql = self._build_delete(pk)
        return self._execute_sync_query(sql).rowcount

    async def delete_async(self, pk: Union[str, int]) -> int:
        """
        Asynchronously delete a record from the database by primary key.
        """
        sql = self._build_delete(pk)
        result = await self._execute_async_query(sql)
        return int(result.rowcount)

    def _build_create(
        self,
        entity: EntityType,
        placeholder: Optional[Literal["index", "string"]] = None,
    ) -> tuple[str, Any]:
        """
        Build the SQL query for creating a new record.
        """
        self.before_create(entity)
        columns = self.get_columns()
        values_names = ", ".join(columns)
        params = self._parse_values(
            **entity.model_dump(include=columns), cast_json=placeholder != "index"
        )
        values = ", ".join(
            [
                f"${idx + 1}" if placeholder == "index" else f"%({col})s"
                for idx, col in enumerate(columns)
            ]
        )
        sql = f"INSERT INTO {self.get_table_name()} ({values_names}) VALUES ({values}) RETURNING *"
        return sql, [
            params.get(col) for col in columns
        ] if placeholder == "index" else params

    def _build_update(
        self,
        pk: Union[int, str],
        entity: EntityType,
        placeholder: Optional[Literal["index", "string"]] = None,
    ) -> tuple[str, Any]:
        """
        Build the SQL query for updating an existing record.
        """
        self.before_update(entity)
        pk = self._validate_pk(pk)
        params = self._parse_values(
            **entity.model_dump(
                exclude={"id", "account", "inboxes"},
                exclude_unset=True,
                exclude_defaults=True,
            )
        )
        if "updated_at" in self.get_columns():
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
        sql = f"UPDATE {self.get_table_name()} SET {values} WHERE id = {pk} RETURNING *"
        return sql, [
            params.get(col) for col in columns
        ] if placeholder == "index" else params

    def _build_delete(self, pk: Union[str, int]) -> str:
        """
        Build the SQL query for deleting a record by primary key.
        """
        pk = self._validate_pk(pk)
        return f"DELETE FROM {self.get_table_name()} WHERE id = {pk}"

    def _validate_pk(self, pk: Union[int, str]) -> int:
        """
        Validate the primary key to ensure it is a positive integer.
        """
        if not str(pk).isdigit() or int(pk) <= 0:
            raise ValueError("Invalid ID. Must be a positive integer.")
        return int(pk)

    def _update_instance_attributes(self, created: Any) -> None:
        """
        Update the instance attributes with the values from the created record.
        """
        for key, value in vars(created).items():
            if isinstance(value, ObjectId):
                value = DocumentID(str(value))
            setattr(self, key, value)

    def _execute_sync_query(self, sql: str, params: Any = None) -> Any:
        """
        Execute a synchronous SQL query.
        """
        with Postgres() as db:
            return db.execute(query=sql, params=params).fetchone()

    async def _execute_async_query(self, sql: str, params: Any = None) -> Any:
        """
        Execute an asynchronous SQL query.
        """
        async with Postgres() as db:
            return await db.fetchrow(sql, *params)
