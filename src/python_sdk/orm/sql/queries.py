from typing import (
    Any,
    AnyStr,
    AsyncIterator,
    Iterator,
    Literal,
    LiteralString,
    Optional,
    Self,
    Type,
    TypeVar,
    Union,
)

from psycopg.types.json import Jsonb
from pydantic import BaseModel, create_model
from typing_extensions import Generic

from ...conf import constants
from ...domain.base.base_model import base_validate_before
from ...infrastructure.db import Postgres
from ...utils import Strings
from ..base import FindAsyncResult, FindResult

EntityType = TypeVar("EntityType", bound=BaseModel)


class SQLQueriesMixin(Generic[EntityType]):
    """
    Mixin class providing SQL query functionalities for entities.
    """

    __selected_columns__: set = set()

    @classmethod
    def _parse_schema(cls, data: Any) -> Self:
        """
        Parse the database record into the entity schema.
        """
        if not data:
            return None
        data = dict(data)

        if not len(cls.__selected_columns__):
            return cls.model_validate(data)
        data = base_validate_before(data)
        fields: dict[str, tuple[Type, Any]] = {}
        for key in cls.__selected_columns__:
            val = data.get(key)
            fields[key] = (type(val), val)

        schema = create_model("Entity", **fields)
        return schema.model_validate(data)

    @classmethod
    def select(cls, *args: AnyStr) -> Self:
        """
        Select specific columns for the query.
        """
        for arg in args:
            column = Strings.to_str(text=arg)
            if column not in cls.get_columns():
                raise ValueError(f"table {cls.get_table_name()} has no column {column}")
            cls.__selected_columns__.add(column)

        return cls

    @classmethod
    def find_by_pk(cls, pk: Union[str, int]) -> Optional[EntityType]:
        """
        Find a record by its primary key.
        """
        try:
            sql, params = cls._build_query(id=pk)
            with Postgres() as db:
                entity = db.execute(sql, params).fetchone()
                return cls._parse_schema(entity)
        finally:
            cls.__selected_columns__.clear()

    @classmethod
    async def find_by_pk_async(cls, pk: Union[str, int]) -> Optional[Self]:
        """
        Asynchronously find a record by its primary key.
        """
        try:
            sql, params = cls._build_query(params_placeholder="index", id=pk)
            async with Postgres() as db:
                entity = await db.fetchrow(sql, *params)
                return cls._parse_schema(entity)
        finally:
            cls.__selected_columns__.clear()

    @classmethod
    def find_one(cls, **kwargs: Any) -> Optional[Self]:
        """
        Find a single record matching the given filters.
        """
        try:
            sql, params = cls._build_query(**kwargs)
            with Postgres() as db:
                entity = db.execute(" ".join([sql, "LIMIT 1"]), params).fetchone()
                return cls._parse_schema(entity)
        finally:
            cls.__selected_columns__.clear()

    @classmethod
    async def find_one_async(cls, **kwargs: Any) -> Optional[Self]:
        """
        Asynchronously find a single record matching the given filters.
        """
        try:
            sql, params = cls._build_query(params_placeholder="index", **kwargs)
            async with Postgres() as db:
                entity = await db.fetchrow(sql, *params)
                return cls._parse_schema(entity)
        finally:
            cls.__selected_columns__.clear()

    @classmethod
    def _find_gen(cls, **kwargs: Any) -> Iterator[Type[Self]]:
        """
        Generator for finding multiple records matching the given filters.
        """
        try:
            sql, params = cls._build_query(**kwargs)
            with Postgres() as db:
                for entity in db.stream(sql, params):
                    if entity:
                        yield cls._parse_schema(entity)
        finally:
            cls.__selected_columns__.clear()

    @classmethod
    async def _find_async_gen(cls, **kwargs: Any) -> AsyncIterator[Type[Self]]:
        """
        Asynchronous generator for finding multiple records matching the given filters.
        """
        try:
            sql, params = cls._build_query(params_placeholder="index", **kwargs)
            async with Postgres() as db:
                async with db.transaction():
                    async for record in db.cursor(sql, *params):
                        yield cls._parse_schema(record)
        finally:
            cls.__selected_columns__.clear()

    @classmethod
    def find(cls, **kwargs: Any) -> FindResult[Type[Self]]:
        """
        Find multiple records matching the given filters.
        """
        return FindResult(lambda: cls._find_gen(**kwargs))

    @classmethod
    def find_async(cls, **kwargs: Any) -> FindAsyncResult[Type[Self]]:
        """
        Asynchronously find multiple records matching the given filters.
        """
        return FindAsyncResult(lambda: cls._find_async_gen(**kwargs))

    @classmethod
    def count(cls, **kwargs: Any) -> int:
        """
        Count the number of records matching the given filters.
        """
        sql, params = cls._build_count_query(params_placeholder="string", **kwargs)
        with Postgres() as db:
            result = db.execute(sql, params).fetchone()
            return (result or {}).get("count", 0)

    @classmethod
    async def count_async(cls, **kwargs: Any) -> int:
        """
        Asynchronously count the number of records matching the given filters.
        """
        sql, params = cls._build_count_query(params_placeholder="index", **kwargs)
        async with Postgres() as db:
            return await db.fetchval(sql, *params)

    @classmethod
    def exists(cls, **kwargs: Any) -> bool:
        """
        Check if any record exists matching the given filters.
        """
        sql, params = cls._build_exists_query(params_placeholder="string", **kwargs)
        with Postgres() as db:
            result = db.execute(sql, params).fetchone()
            return (result or {}).get("exists", False)

    @classmethod
    async def exists_async(cls, **kwargs: Any) -> bool:
        """
        Asynchronously check if any record exists matching the given filters.
        """
        sql, params = cls._build_exists_query(params_placeholder="index", **kwargs)
        async with Postgres() as db:
            return await db.fetchval(sql, *params)

    @classmethod
    def _build_count_query(
        cls,
        params_placeholder: Optional[Literal["index", "string"]] = None,
        **kwargs: Any,
    ) -> tuple[LiteralString, list[Any]]:
        """
        Build the SQL query for counting records.
        """
        cls.__selected_columns__.clear()
        select_query, params = cls._build_query(
            params_placeholder=params_placeholder, **kwargs
        )

        count_query = select_query.replace("*", "COUNT(*)", 1)
        return count_query, params

    @classmethod
    def _build_exists_query(
        cls,
        params_placeholder: Optional[Literal["index", "string"]] = None,
        **kwargs: Any,
    ) -> tuple[LiteralString, list[Any]]:
        """
        Build the SQL query for checking record existence.
        """
        sql: Any = f"SELECT EXISTS(SELECT 1 FROM {cls.get_table_name()}"
        cls.__selected_columns__.clear()
        params = []
        if kwargs:
            sql += " WHERE"
            counter = 1
            for key, value in kwargs.items():
                param = f"${counter}" if params_placeholder == "index" else "%s"
                field, operator = cls._parse_filter(key)
                sql += f" {field} {operator} {param}"
                counter += 1
                params.append(value)
        sql += ")"

        return sql, params

    @classmethod
    def _build_query(
        cls,
        params_placeholder: Optional[Literal["index", "string"]] = None,
        **kwargs: Any,
    ) -> tuple[LiteralString, list[Any]]:
        """
        Build the SQL query for selecting records.
        """
        select = (
            "*"
            if not len(cls.__selected_columns__)
            else ", ".join(cls.__selected_columns__)
        )

        sql: LiteralString = f"SELECT {select} FROM {cls.get_table_name()}"  # type: ignore
        params = []  # noqa

        if kwargs:
            sql += " WHERE"
            counter = 1
            for key, value in kwargs.items():
                param = f"${counter}" if params_placeholder == "index" else "%s"
                field, operator = cls._parse_filter(key)
                prefix = " AND" if counter > 1 else ""
                sql += f"{prefix} {field} {operator} {param}"
                counter += 1
                params.append(value)

        return sql, params

    @classmethod
    def _parse_values(cls, cast_json: bool = True, **kwargs) -> dict[str, Any]:
        """
        Parse values for SQL queries, casting JSON fields if necessary.
        """
        return {
            key: Jsonb(value)
            if isinstance(value, (list, dict)) and cast_json
            else value
            for key, value in kwargs.items()
        }

    @classmethod
    def _parse_filter(cls, key: str) -> tuple[str, str]:
        """
        Parse filter keys into SQL field and operator.
        """
        parts = key.split("__")
        field = parts[0]
        lookup = parts[1] if len(parts) > 1 else "eq"
        field = "id" if field == "pk" else field
        operator = (
            constants.SQL_OPERATORS[lookup]
            if lookup in constants.SQL_OPERATORS
            else "="
        )

        return field, operator
