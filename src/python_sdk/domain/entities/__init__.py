from typing import Any, LiteralString, cast

from pydantic import Field

from ...errors import NoIdError
from ...orm.sql.commands import SQLCommandsMixin
from ...orm.sql.queries import SQLQueriesMixin
from ...utils import DateTime, Strings
from ..base.base_model import BaseModel
from ..base.fields import DateTimeField, EntityIDField


class BaseEntity(BaseModel):
    id: EntityIDField = Field(
        default=None, title="Id", description="The primary key of the table."
    )

    @classmethod
    def get_columns(cls) -> set[str]:
        return set(sorted((cast(dict, cls.model_fields)).keys()))

    @classmethod
    def get_table_name(cls) -> str:
        return getattr(
            cls,
            "__tablename__",
            Strings.to_snake_case(Strings.to_plural(cls.__name__)),
        )


class SQLModel(BaseEntity, SQLQueriesMixin, SQLCommandsMixin):
    """
    Base SQL Model class that combines entity, query, and command functionalities.
    """

    def _find_by_pk_sql(self) -> tuple[LiteralString, tuple[Any]]:
        """
        Build SQL query to find a record by primary key.
        """
        return f"SELECT * FROM {self.get_table_name} WHERE id = %s", (self.id,)  # noqa

    def refresh_from_db(self) -> None:
        """
        Refresh the current instance with data from the database.
        """
        if self.id is None:
            raise NoIdError(self.get_table_name())

        record = self.find_by_pk(self.id)

        for k, v in record.items():
            setattr(self, k, v)

    async def refresh_from_db_async(self) -> None:
        """
        Asynchronously refresh the current instance with data from the database.
        """
        if self.id is None:
            raise NoIdError(self.get_table_name())

        record = await self.find_by_pk_async(self.id)

        for k, v in record.items():
            setattr(self, k, v)


class SQLTimeStampedModel(SQLModel):
    """
    SQL Model with timestamp fields for creation and updates.
    """

    created_at: DateTimeField = Field(
        default_factory=DateTime.now,
        title="Created At",
        description="The date and time the record was created.",
    )
    updated_at: DateTimeField = Field(
        default_factory=DateTime.now,
        title="Updated At",
        description="The date and time the record was last updated.",
    )
