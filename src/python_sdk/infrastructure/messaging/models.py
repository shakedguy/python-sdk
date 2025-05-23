from __future__ import annotations

from typing import Any, Generic, Optional, Self, TypeVar, Union

from pydantic import Field, model_validator

from ...domain.base.base_model import BaseModel, base_validate_before
from ...domain.base.fields import DateTimeField, UUIDField
from ...utils import Crypto, DateTime


class BaseMessageBody(BaseModel):
    """
    Base class for message bodies.
    This class is used to define the structure of message bodies.
    Attributes:
        id (UUIDField): The unique identifier of the message.
        timestamp (DateTimeField): The time when the message was created.
    """

    id: UUIDField = Field(
        default_factory=Crypto.uuid7,
        title="Message ID",
        description="The unique identifier of the message",
    )

    sender: Optional[str] = Field(
        default_factory=str, title="Sender", description="Sender of the message"
    )

    timestamp: DateTimeField = Field(
        default_factory=DateTime.now,
        title="Timestamp",
        description="The time when the message was created",
    )


MessageBody = TypeVar("MessageBody", bound=BaseMessageBody)


class BaseMessage(BaseModel, Generic[MessageBody]):
    """
    Base class for broker messages.
    This class is used to define the structure of messages sent to and from the broker.
    Attributes:
        id (UUIDField): The unique identifier of the message.
        pattern (str): The pattern of the message.
        data (MessageBody | dict[str, Any]): The body of the message.
        timestamp (DateTimeField): The time when the message was created.
    """

    id: UUIDField = Field(
        default_factory=Crypto.uuid7,
        title="Message ID",
        description="The unique identifier of the message",
    )

    pattern: str = Field(
        default_factory=str, title="Pattern", description="Message pattern"
    )

    data: Union[MessageBody, dict[str, Any]] = Field(
        default_factory=dict, title="Data", description="Message data"
    )
    timestamp: DateTimeField = Field(
        default_factory=DateTime.now,
        title="Timestamp",
        description="The time when the message was created",
    )

    @model_validator(mode="before")
    @classmethod
    def validate_before(
        cls, value: Union[Self, dict[str, Any]]
    ) -> Union[Self, dict[str, Any]]:
        if isinstance(value, BaseMessage):
            return value

        value = base_validate_before(value)
        value.setdefault("id", Crypto.uuid7())
        value.setdefault("timestamp", DateTime.utc_now())
        value.setdefault("data", dict())
        value["data"]["id"] = value["data"].get("id", value["id"])
        value["data"]["timestamp"] = value["data"].get("timestamp", value["timestamp"])

        return value
