from __future__ import annotations

from typing import Any, Optional

from pydantic import Field, model_validator

from ..base.base_model import BaseModel, base_validate_before
from ..base.fields import EntityIDField, JsonField
from .base import BaseMessage


class ProcessMessageEvent(BaseMessage):
    account_id: EntityIDField = Field(
        ..., title="Account ID", description="The unique identifier of the account"
    )
    inbox_id: EntityIDField = Field(
        ..., title="Inbox ID", description="The unique identifier of the inbox"
    )
    conversation_id: EntityIDField = Field(
        ...,
        title="Conversation ID",
        description="The unique identifier of the conversation",
    )
    message_id: EntityIDField = Field(
        ...,
        title="Message ID",
        description="The unique identifier of the message",
    )
    contact_id: EntityIDField = Field(
        ..., title="Contact ID", description="The unique identifier of the contact"
    )

    message_type: Optional[str] = Field(
        default_factory=str,
        title="Message Type",
        description="The type of the message",
    )

    message_status: Optional[str] = Field(
        default_factory=str,
        title="Message Status",
        description="The status of the message",
    )

    attachment: Optional[Attachment] = Field(
        default=None,
        title="Attachment",
        description="The attachment associated with the message",
    )

    channel: Optional[str] = Field(
        default_factory=str,
        title="Channel",
        description="The channel through which the message was sent",
    )

    event: Optional[str] = Field(
        default_factory=str,
        title="Event",
        description="The event associated with the message",
    )
    sender_type: Optional[str] = Field(
        default_factory=str,
        title="Sender Type",
        description="The type of the sender",
    )
    content_attributes: Optional[dict[str, Any]] = Field(
        default_factory=dict,
        title="Content Attributes",
        description="The attributes of the content",
    )
    source_id: Optional[str] = Field(
        default_factory=str,
        title="Source ID",
        description="The source ID of the message",
    )


class Attachment(BaseModel):
    id: Optional[EntityIDField] = Field(
        default=None,
        title="Attachment ID",
        description="The unique identifier of the attachment",
    )
    message_id: Optional[EntityIDField] = Field(
        default=None,
        title="Message ID",
        description="The unique identifier of the message",
    )

    file_type: Optional[str] = Field(
        default=None,
        title="File Type",
        description="The type of the file",
    )

    account_id: Optional[EntityIDField] = Field(
        default=None,
        title="Account ID",
        description="The unique identifier of the account",
    )
    fallback_title: Optional[str] = Field(
        default=None,
        title="Fallback Title",
        description="The fallback title of the attachment",
    )
    extension: Optional[str] = Field(
        default=None,
        title="Extension",
        description="The extension of the attachment",
    )
    data_url: Optional[str] = Field(
        default=None,
        title="Data URL",
        description="The data URL of the attachment",
    )
    thumb_url: Optional[str] = Field(
        default=None,
        title="Thumbnail URL",
        description="The thumbnail URL of the attachment",
    )
    file_size: Optional[EntityIDField] = Field(
        default=None,
        title="File Size",
        description="The size of the file",
    )
    width: Optional[EntityIDField] = Field(
        default=None,
        title="Width",
        description="The width of the attachment",
    )
    height: Optional[EntityIDField] = Field(
        default=None,
        title="Height",
        description="The height of the attachment",
    )


class ChangedAttributes(BaseModel):
    previous_value: dict[str, Any] = Field(
        default_factory=dict,
        title="Previous Value",
        description="The previous value of the attribute",
    )
    current_value: dict[str, Any] = Field(default_factory=dict, title="Current Value")


class ContactUpdatedEvent(BaseMessage):
    account_id: EntityIDField = Field(
        ..., title="Account ID", description="The unique identifier of the account"
    )
    contact_id: EntityIDField = Field(
        ..., title="Contact ID", description="The unique identifier of the contact"
    )
    changed_attributes: Optional[list[dict[str, ChangedAttributes]]] = Field(
        default_factory=list,
        title="Changed Attributes",
        description="The attributes that were changed",
    )

    @model_validator(mode="before")
    @classmethod
    def validate_before(cls, data: Any) -> Any:
        data = base_validate_before(data)
        if "data" in data:
            data = data["data"]
        if "account" in data:
            data["account_id"] = data.get("account", {}).get("id", None)

        if "id" in data:
            data["contact_id"] = data.get("id", None)

        return data


class ContactCreatedEvent(BaseMessage):
    account_id: EntityIDField = Field(
        ..., title="Account ID", description="The unique identifier of the account"
    )
    contact_id: EntityIDField = Field(
        ..., title="Contact ID", description="The unique identifier of the contact"
    )

    @model_validator(mode="before")
    @classmethod
    def validate_before(cls, data: Any) -> Any:
        data = base_validate_before(data)
        if "data" in data:
            data = data["data"]
        if "account" in data:
            data["account_id"] = data.get("account", {}).get("id", None)

        if "id" in data:
            data["contact_id"] = data.get("id", None)
        return data


class WebhookEvent(BaseMessage):
    account_id: Optional[EntityIDField] = Field(
        default=None,
        title="Account ID",
        description="The unique identifier of the account",
    )
    contact_id: Optional[EntityIDField] = Field(
        default=None,
        title="Contact ID",
        description="The unique identifier of the contact",
    )
    data: Optional[JsonField] = Field(
        default=None, title="Data", description="The data associated with the event"
    )
    event: Optional[str] = Field(
        default=None, title="Event", description="The name of the event"
    )
