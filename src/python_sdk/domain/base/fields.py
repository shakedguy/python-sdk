from datetime import datetime
from typing import Annotated, Any, Optional, TypeVar, Union
from uuid import UUID

from pydantic import (
    BeforeValidator,
    GetCoreSchemaHandler,
    GetJsonSchemaHandler,
    JsonValue,
    PlainSerializer,
)
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, core_schema, from_json
from pydantic_core.core_schema import (
    ValidationInfo,
)

from ...conf.constants import BSON_EXISTS
from ...utils import DateTime
from ...utils.crypto import to_object_id_str, uuidv7
from ...utils.strings import to_str

if BSON_EXISTS:
    from bson.objectid import ObjectId
else:
    from .object_id import ObjectId

T = TypeVar("T")

SetField = Annotated[
    set[T],  # noqa
    BeforeValidator(lambda x: set(x) if x else set()),
    PlainSerializer(lambda x: list(x)),
]

JSONPrimitive = Union[str, int, float, bool, None]

JSONObject = dict[str, JSONPrimitive]

JSONArray = list[JSONPrimitive]

JSONPayload = Union[JSONObject | JSONArray]


def to_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    return DateTime.to_datetime(value)


DateTimeField = Annotated[
    Optional[datetime],
    BeforeValidator(to_datetime),
]

DateTimeISOStrField = Annotated[
    Optional[str],
    BeforeValidator(
        lambda x: DateTime.to_datetime(x).isoformat() if x else DateTime.iso_now()
    ),
]

DateOnlyStrField = Annotated[
    Optional[str],
    BeforeValidator(
        lambda x: DateTime.to_date_only(x).strftime("%Y-%m-%d") if x else None
    ),
]

TimeOnlyStrField = Annotated[
    Optional[str],
    BeforeValidator(
        lambda x: DateTime.to_time_only(x).strftime("%H:%M:%S") if x else None
    ),
]


def _parse_timestamp(value: Any) -> datetime:
    if not value:
        return DateTime.utc_now()
    try:

        if isinstance(value, datetime):
            return value
        return DateTime.to_datetime(value)
    except (ValueError, TypeError):
        pass
    return DateTime.utc_now()


TimestampField = Annotated[
    datetime,
    BeforeValidator(_parse_timestamp),
    PlainSerializer(lambda x: x.timestamp())
]


def _parse_entity_id(value: Any) -> Optional[Union[int, str]]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, (DocumentID, UUID)):
        return str(value)
    if BSON_EXISTS and isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, (str, bytes, bytearray, memoryview)):
        val = to_str(value)
        return int(val) if val.isnumeric() else val
    return str(value)


EntityIDField = Annotated[
    Optional[Union[int, str]], BeforeValidator(_parse_entity_id)
]


def to_default_entity_id(value: Any) -> Union[str, int]:
    if value is None or isinstance(value, (UUID, str)):
        return value or uuidv7()
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return value.decode("utf-8")
    return str(value)


DefaultEntityIDField = Annotated[
    Union[str, int], BeforeValidator(to_default_entity_id)
]

FloatField = Annotated[
    Optional[float], BeforeValidator(lambda x: float(x) if x else None)
]


def _parse_json_field(value: Any) -> Optional[JsonValue]:
    if isinstance(value, (str, bytes, bytearray, memoryview)):
        try:
            return from_json(value)
        except ValueError:
            pass

    return value if isinstance(value, (dict, list)) else None


JsonObjectField = Annotated[
    Optional[JSONObject],
    BeforeValidator(_parse_json_field),
]

ChannelVersionsField = Annotated[
    Optional[dict[str, Union[str, int, float]]],
    BeforeValidator(lambda x: dict(x) if x else dict()),
]

JsonArrayField = Annotated[
    Optional[list[dict[str, Any]]],
    BeforeValidator(_parse_json_field),
]

JsonField = Annotated[JsonValue, BeforeValidator(_parse_json_field)]

UUIDField = Annotated[
    Optional[str], BeforeValidator(lambda x: str(x) if x is not None else None)
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
        except Exception as e:
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
        return DocumentID(to_object_id_str(id_))


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


DocumentIDField = Annotated[
    Optional[DocumentID],
    BeforeValidator(_create_document_id),
    PlainSerializer(
        when_used="json-unless-none",
        func=lambda v: str(v) if v else None,
    ),
]
