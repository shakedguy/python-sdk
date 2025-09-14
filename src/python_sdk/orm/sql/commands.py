import asyncio
from typing import Any, Collection, Generic, Literal, Optional, Self, TypeVar, Union

from pydantic import BaseModel

from ...infrastructure.db import Postgres
from ...utils import DateTime
from .parsers import parse_values

EntityType = TypeVar("EntityType", bound=BaseModel)


class SQLCommandsMixin(Generic[EntityType]):  # noqa
    """
    Mixin class providing SQL command functionalities for entities.
    """

    def save(self) -> None:
        """
        Save the current instance to the database.
        """

        _id = getattr(self, "id", None)
        if _id is None:
            created = self.create(self)  # type: ignore
            self._update_instance_attributes(created)
        else:
            self.update(_id, self)  # type: ignore

    async def save_async(self) -> None:
        """
        Asynchronously save the current instance to the database.
        """

        _id = getattr(self, "id", None)

        if _id is None:
            created = self.create_async(self)  # type: ignore
            self._update_instance_attributes(created)
        else:
            await self.update_async(_id, self)  # type: ignore

    @classmethod
    def create(cls, entity: EntityType) -> Optional[Self]:
        """
        Create a new record in the database.
        """
        if not entity:
            return None
        if hasattr(entity, "before_insert"):
            entity.before_insert()
        sql, params = cls._build_create(entity)
        result = cls._execute_sync_query(sql, params)

        return cls._parse_schema(result) if result else None  # type: ignore

    @classmethod
    def create_many(cls, entities: Collection[EntityType]) -> Optional[Union[list[str], list[int]]]:
        """
        Create multiple new records in the database.
        """
        if not entities:
            return None
        for entity in entities:
            if hasattr(entity, "before_insert"):
                entity.before_insert()
        sql, params = cls._build_create_many(list(entities))
        with Postgres() as db:
            result = db.execute(query=sql, params=params, returning=True).fetchall()  # type: ignore

        if result:
            return [
                int(row['id'])
                if isinstance(row['id'], str) and str(row["id"]).isnumeric()
                else row['id']
                for row in result
            ]
        return None

    @classmethod
    async def create_many_async(cls, entities: Collection[EntityType]) -> Optional[Union[list[str], list[int]]]:
        """
        Asynchronously create multiple new records in the database.
        """
        if not entities:
            return None

        tasks = []

        for entity in entities:
            if hasattr(entity, "before_insert_async"):
                tasks.append(entity.before_insert_async())

        if tasks:
            await asyncio.gather(*tasks)

        sql, params = cls._build_create_many(list(entities), placeholder="index")
        async with Postgres() as db:
            result = await db.fetch(sql, *params)

        if result:
            return [
                int(row['id'])
                if isinstance(row['id'], str) and str(row["id"]).isnumeric()
                else row['id']
                for row in result
            ]
        return None

    @classmethod
    async def create_async(cls, entity: EntityType) -> Optional[Self]:
        """
        Asynchronously create a new record in the database.
        """
        if not entity:
            return None

        if hasattr(entity, "before_insert_async"):
            await entity.before_insert_async()
        sql, params = cls._build_create(entity, placeholder="index")
        result = await cls._execute_async_query(sql, params)

        return cls._parse_schema(result) if result else None  # type: ignore

    @classmethod
    def update(cls, pk: Union[int, str], entity: EntityType) -> Optional[Self]:
        """
        Update an existing record in the database.
        """
        if not entity:
            return None
        if hasattr(entity, "before_update"):
            entity.before_update()
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
        if hasattr(entity, "before_update_async"):
            await entity.before_update_async()
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

        if hasattr(entity, "get_columns"):
            columns = entity.get_columns()
        else:
            columns = set(vars(entity).keys())

        _id = getattr(entity, "id", None)
        if isinstance(_id, str) and _id is not None and len(_id) > 0:
            columns = set(["id"] + list(columns))
        elif not _id:
            columns.remove("id")

        params = parse_values(
            **entity.model_dump(include=columns), cast_json=placeholder != "index"
        )
        values = ", ".join(
            [
                f"${idx + 1}" if placeholder == "index" else f"%({col})s"
                for idx, col in enumerate(columns)
            ]
        )
        values_names = ", ".join(columns)
        sql = f"INSERT INTO {entity.get_table_name()} ({values_names}) VALUES ({values}) RETURNING *"  # noqa
        return sql, [
            params.get(col) for col in columns
        ] if placeholder == "index" else params

    @classmethod
    def _build_create_many(
            cls,
            entities: list[EntityType],
            placeholder: Optional[Literal["index", "string"]] = None,
    ) -> tuple[str, Any]:
        """
        Build the SQL query for creating multiple new records.
        """

        if not entities:
            raise ValueError("Entities list cannot be empty.")

        first_entity = entities[0]
        if hasattr(first_entity, "get_columns"):
            columns = first_entity.get_columns()
        else:
            columns = set(vars(first_entity).keys())

        columns.remove("id")
        columns = set(sorted(columns))
        values_names = ", ".join(columns)
        params = []
        values_list = []
        if placeholder != "index":

            values = ", ".join([f"%s" for _ in columns])
            sql = f"INSERT INTO {first_entity.get_table_name()} ({values_names}) VALUES ({values}) RETURNING id"  # noqa
            params = []
            for entity in entities:
                entity_params = parse_values(
                    **entity.model_dump(include=columns), cast_json=True
                )
                params.append(tuple(entity_params.get(col) for col in columns))
            return sql, params

        for entity in entities:
            entity_params = parse_values(
                **entity.model_dump(include=columns), cast_json=placeholder != "index"
            )
            params.extend(tuple(entity_params.get(col) for col in columns))
            values = ", ".join(
                [
                    f"${len(params) - len(columns) + idx + 1}"
                    for idx, col in enumerate(columns)
                ]
            )
            values_list.append(f"({values})")
        values_str = ", ".join(values_list)

        sql = f"INSERT INTO {first_entity.get_table_name()} ({values_names}) VALUES {values_str} RETURNING id"  # noqa
        return sql, params

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

        pk = cls._validate_pk(pk)
        params = parse_values(
            **entity.model_dump(
                exclude={"id", "account", "inboxes"},
                exclude_unset=True,
                exclude_defaults=True,
            )
        )
        columns = cls.get_columns() if hasattr(cls, "get_columns") else set(vars(cls).keys())
        if "updated_at" in columns:
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
        sql = f"UPDATE {cls.get_table_name()} SET {values} WHERE id = {pk_value} RETURNING *"  # noqa
        return sql, [
            params.get(col) for col in columns
        ] if placeholder == "index" else params

    @classmethod
    def _build_delete(cls, pk: Union[str, int]) -> str:
        """
        Build the SQL query for deleting a record by primary key.
        """
        pk = cls._validate_pk(pk)
        return f"DELETE FROM {cls.get_table_name()} WHERE id = {pk}"  # noqa

    @classmethod
    def _validate_pk(cls, pk: Union[int, str]) -> Union[int, str]:
        """
        Validate the primary key to ensure it is a positive integer.
        """
        if not pk or str(pk) == "":
            raise ValueError("ID cannot be empty or None.")
        return int(pk) if str(pk).isdigit() else pk

    def _update_instance_attributes(self, created: Any) -> None:
        """
        Update the instance attributes with the values from the created record.
        """

        if hasattr(created, "get_columns"):
            columns = created.get_columns()
        else:
            columns = set(vars(created).keys())
        for column in columns:
            setattr(self, column, getattr(created, column))

    @classmethod
    def _execute_sync_query(cls, sql: str, params: Any = None) -> Any:
        """
        Execute a synchronous SQL query.
        """
        with Postgres() as db:
            return db.execute(query=sql, params=params).fetchone()  # type: ignore

    @classmethod
    async def _execute_async_query(cls, sql: str, params: Any = None) -> Any:
        """
        Execute an asynchronous SQL query.
        """
        async with Postgres() as db:
            return await db.fetchrow(sql, *params)
