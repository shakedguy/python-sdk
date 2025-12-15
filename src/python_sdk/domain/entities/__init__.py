from typing import Any, Collection, LiteralString, Optional, Sequence, cast, override

from pydantic import Field

from ...errors import NoIdError
from ...orm.sql.commands import SQLCommandsMixin
from ...orm.sql.queries import SQLQueriesMixin
from ...utils import DateTime, enums
from ...utils.strings import to_plural, to_snake_case
from ..base.base_model import BaseModel
from ..base.fields import DateTimeField, EntityIDField


class EntityIndexType(enums.StrEnum):
    BTREE = "btree"
    HASH = "hash"
    GIST = "gist"
    GIN = "gin"
    SPGIST = "spgist"
    BRIN = "brin"

    @property
    def sql_value(self) -> str:
        mapping = {
            EntityIndexType.BTREE: "btree",
            EntityIndexType.HASH: "hash",
            EntityIndexType.GIST: "gist",
            EntityIndexType.GIN: "gin",
            EntityIndexType.SPGIST: "spgist",
            EntityIndexType.BRIN: "brin",
        }
        return mapping[self]


class EntityIndex(BaseModel):
    """
    Represents an index for an SQL entity.
    This class defines the structure of an index, including its name, type, and columns.
    It is used to create and manage indexes in SQL databases.

    Attributes:
        name (str): The name of the index.
        unique (Optional[bool]): Indicates if the index is unique.
        type (EntityIndexType): The type of the index, such as BTREE or HASH
        columns (Sequence[str]): The columns that the index is built on.
    Example:
        index = EntityIndex(
            name="my_index",
            unique=True,
            type=EntityIndexType.BTREE,
            columns=["column1", "column2"]
        )
    """

    name: str = Field(..., title="Name", description="The index name.")

    unique: Optional[bool] = Field(
        default=False, title="Unique", description="The index is unique."
    )
    type: EntityIndexType = Field(default=EntityIndexType.BTREE, title="Type", description="The index type.")

    columns: Sequence[str] = Field(..., title="Keys", description="The index keys.")


class BaseEntity(BaseModel):
    class Meta:
        table_name: str = ""
        indexes: Collection[EntityIndex] = list()
        exclude: Collection[str] = list()

    id: EntityIDField = Field(
        default=None, title="Id", description="The primary key of the table."
    )

    @classmethod
    def get_table_name(cls) -> str:
        return getattr(
            cls.Meta,
            "table_name",
            to_snake_case(to_plural(cls.__name__)),
        )

    @classmethod
    def get_exclude_fields(cls) -> set[str]:

        val = getattr(cls.Meta, "exclude", [])
        if not isinstance(val, (list, set, tuple)):
            raise ValueError("Meta.exclude must be a list, set, or tuple")
        return set(val)

    @classmethod
    def get_columns(cls) -> set[str]:
        all_columns = list(sorted((cast(dict, cls.model_fields)).keys()))
        exclude_columns = cls.get_exclude_fields()
        return set([col for col in all_columns if col not in exclude_columns])




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


    def before_update(self) -> None: ...

    def before_insert(self) -> None: ...

    async def before_update_async(self) -> None: ...

    async def before_insert_async(self) -> None: ...

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

    @override  # noqa
    def before_update(self) -> None:
        super().before_update()
        self.updated_at = DateTime.now()

    @override  # noqa
    def before_insert(self) -> None:
        super().before_insert()
        self.created_at = DateTime.now()

    @override  # noqa
    async def before_update_async(self) -> None:
        await super().before_update_async()
        self.updated_at = DateTime.now()

    @override  # noqa
    async def before_insert_async(self) -> None:
        await super().before_insert_async()
        self.created_at = DateTime.now()