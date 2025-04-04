from __future__ import annotations

from functools import cached_property
from typing import Any, Literal, Union, cast

from bson.objectid import ObjectId
from pydantic import (
    BaseModel as PydanticBaseModel,
)
from pydantic import (
    ConfigDict,
    Field,
    model_serializer,
    model_validator,
)

from ...utils import ChangeKeysCase, DateTime, dict_or_pydantic_model_to_dict, mixins
from .fields import DateTimeField, DocumentID


def base_validate_before(
    data: Union[PydanticBaseModel, dict[str, Any]],
) -> dict[str, Any]:
    if not isinstance(data, (PydanticBaseModel, dict)):
        raise ValueError("Invalid data type, must be a dict or Pydantic model")
    res = ChangeKeysCase.to_snake_case(dict_or_pydantic_model_to_dict(data), deep=False)

    return res


def _serialize_field(value: Any, mode: Literal["json", "dict"] = "dict") -> Any:
    if isinstance(value, (PydanticBaseModel, dict, list, set, tuple)):
        return base_serializer(value)
    if isinstance(value, (ObjectId, DocumentID)):
        return DocumentID(str(value)) if mode == "dict" else str(value)
    return value


def base_serializer(
    model: Union[
        PydanticBaseModel,
        dict[str, Any],
        list[Union[PydanticBaseModel, dict[str, Any]]],
    ],
    mode: Literal["json", "dict"] = "dict",
) -> Any:
    if isinstance(model, (list, set, tuple)):
        return [base_serializer(item) for item in model]

    if not isinstance(model, (PydanticBaseModel, dict)):
        return model

    res = dict()
    if isinstance(model, PydanticBaseModel):
        for key, field in model.model_computed_fields.items():
            field_name = field.alias or key
            value = getattr(model, key)
            res[field_name] = _serialize_field(value, mode)

        for key, field in model.model_fields.items():
            value = getattr(model, key)
            field_name = field.alias or key
            res[field_name] = _serialize_field(value, mode)

    else:
        for key, value in model.items():
            res[key] = _serialize_field(value, mode)

    return res


class BaseModel(PydanticBaseModel, mixins.DictMixin):
    model_config = ConfigDict(
        from_attributes=False,
        validate_assignment=True,
        extra="allow",
        populate_by_name=True,
        ser_json_timedelta="iso8601",
    )

    @model_validator(mode="before")
    @classmethod
    def validate_before(
        cls, data: Union[PydanticBaseModel, dict[str, Any]]
    ) -> dict[str, Any]:
        return base_validate_before(data)

    @classmethod
    def model_fields_set(cls) -> set[str]:
        return set(sorted((cast(dict, cls.model_fields)).keys()))

    @model_serializer
    def ser_model(self) -> dict[str, Any]:
        return base_serializer(self)

    @model_serializer(when_used="json-unless-none")
    def ser_model_json(self) -> dict[str, Any]:
        return base_serializer(self, mode="json")

    @cached_property
    def flatten(self) -> dict[str, Any]:
        return ChangeKeysCase.flatten_all_cases(base_serializer(self))


class TimestampModel(BaseModel):
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
