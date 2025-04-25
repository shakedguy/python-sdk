from typing import Any, LiteralString

from pydantic import Field

from ... import errors
from ...domain.base.fields import DateTimeField
from ...utils import DateTime
from .base_entity import BaseEntity
from .commands import SQLCommandsMixin
from .queries import SQLQueriesMixin


class SQLModel(BaseEntity, SQLQueriesMixin, SQLCommandsMixin):
    """
    Base SQL Model class that combines entity, query, and command functionalities.
    """

    def _find_by_pk_sql(self) -> tuple[LiteralString, tuple[Any]]:
        """
        Build SQL query to find a record by primary key.
        """
        return f"SELECT * FROM {self.get_table_name} WHERE id = %s", (self.id,)  # type: ignore

    def refresh_from_db(self) -> None:
        """
        Refresh the current instance with data from the database.
        """
        if self.id is None:
            raise errors.NoIdError(self.get_table_name)

        record = self.find_by_pk(self.id)

        for k, v in record.items():
            setattr(self, k, v)

    async def refresh_from_db_async(self) -> None:
        """
        Asynchronously refresh the current instance with data from the database.
        """
        if self.id is None:
            raise errors.NoIdError(self.get_table_name)

        record = await self.find_by_pk_async(self.id)

        for k, v in record.items():
            setattr(self, k, v)


class SQLTimeStampedModel(SQLModel):
    """
    SQL Model with timestamp fields for creation and updates.
    """

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
