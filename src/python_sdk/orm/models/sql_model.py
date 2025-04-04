from typing import Any, LiteralString

from pydantic import Field

from ... import errors
from ...utils import DateTime, Strings
from .fields import DateTimeField, EntityID
from .model import BaseModel


class SQLModel(BaseModel):
    id: EntityID = Field(
        default=None, title="Id", description="The primary key of the table."
    )

    @classmethod
    def get_table_name(cls) -> str:
        return getattr(
            cls,
            "__tablename__",
            Strings.to_snake_case(Strings.to_plural(cls.__name__)),
        )

    def _find_by_pk_sql(self) -> tuple[LiteralString, tuple[Any]]:
        return f"SELECT * FROM {self.get_table_name()} WHERE id = %s", (self.id,)  # type: ignore

    def refresh_from_db(self) -> None:
        if self.id is None:
            raise errors.NoIdError(self.get_table_name())

        from ...infrastructure.db import Postgres

        sql, params = self._find_by_pk_sql()
        with Postgres() as db:
            record = db.execute(
                sql,
                params,
            ).fetchone()
            if record is None:
                raise errors.NotExistsError(self.get_table_name(), self.id)

        for k, v in record.items():
            setattr(self, k, v)

    async def refresh_from_db_async(self) -> None:
        if self.id is None:
            raise errors.NoIdError(self.get_table_name())

        from ...infrastructure.db import Postgres

        sql, params = self._find_by_pk_sql()
        async with Postgres() as db:
            record = await db.fetchrow(sql, params)
            if record is None:
                raise errors.NotExistsError(self.get_table_name(), self.id)

        for k, v in record.items():
            setattr(self, k, v)


class SQLTimeStampedModel(SQLModel):
    created_at: DateTimeField = Field(
        default=DateTime.now(),
        title="Created At",
        description="The date and time the record was created.",
    )
    updated_at: DateTimeField = Field(
        default=DateTime.now(),
        title="Updated At",
        description="The date and time the record was last updated.",
    )
