from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Optional, TypeVar, Union

from bson import ObjectId
from bson.errors import InvalidId
from pydantic import (
    BeforeValidator,
    GetCoreSchemaHandler,
    GetJsonSchemaHandler,
    JsonValue,
    PlainSerializer,
    PositiveInt,
)
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, core_schema, from_json
from pydantic_core.core_schema import (
    ValidationInfo,
)

from ...utils import Crypto, DateTime

T = TypeVar("T")

SetField = Annotated[
    set[T],
    BeforeValidator(lambda x: set(x) if x else set()),
    PlainSerializer(lambda x: list(x)),
]

JSONPrimitive = Union[str, int, float, bool, None]

JSONObject = dict[str, JSONPrimitive]

JSONArray = list[JSONPrimitive]

JSONValue = Union[JSONPrimitive | JSONObject | JSONArray]

JSONPayload = Union[JSONObject | JSONArray]


DateTimeField: Optional[datetime] = Annotated[
    Optional[datetime],
    BeforeValidator(lambda x: DateTime.to_app_timezone(x) if x else None),
]

EntityID: Optional[PositiveInt] = Annotated[
    Optional[PositiveInt], BeforeValidator(lambda x: int(x) if x else None)
]


def _parse_json_field(value: Any) -> JsonValue:
    if isinstance(value, str):
        try:
            return from_json(value)
        except ValueError:
            pass

    return value


JsonObjectField: Optional[dict[str, Any]] = Annotated[
    Optional[dict[str, Any]],
    BeforeValidator(_parse_json_field),
]

JsonArrayField: Optional[list[dict[str, Any]]] = Annotated[
    Optional[list[dict[str, Any]]],
    BeforeValidator(_parse_json_field),
]

JsonField: JsonValue = Annotated[JsonValue, BeforeValidator(_parse_json_field)]


UUIDField: Optional[str] = Annotated[
    Optional[str], BeforeValidator(lambda x: str(x or Crypto.uuid7()))
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
        except (InvalidId, TypeError) as e:
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


DocumentIDField: Optional[DocumentID] = Annotated[
    Optional[DocumentID],
    BeforeValidator(_create_document_id),
    PlainSerializer(
        when_used="json-unless-none",
        func=lambda v: str(v) if v else None,
    ),
]

# RelatedField: Optional[DocumentID] = Annotated[
#     Optional[DocumentID],
#     BeforeValidator(_create_document_id),
# ]
