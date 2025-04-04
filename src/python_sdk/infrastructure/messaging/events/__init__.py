from typing import Optional

from pydantic import Field

from ....domain import BaseModel, DateTimeField, EntityID, JsonField, UUIDField


class Event(BaseModel):
    id: UUIDField = Field(
        ..., title="Message ID", description="The unique identifier of the message"
    )
    timestamp: DateTimeField = Field(
        ..., title="Timestamp", description="The time when the message was created"
    )


class ProcessMessageEvent(Event):
    account_id: EntityID = Field(
        ..., title="Account ID", description="The unique identifier of the account"
    )
    inbox_id: EntityID = Field(
        ..., title="Inbox ID", description="The unique identifier of the inbox"
    )
    conversation_id: EntityID = Field(
        ...,
        title="Conversation ID",
        description="The unique identifier of the conversation",
    )
    message_id: EntityID = Field(
        ...,
        title="Message ID",
        description="The unique identifier of the message",
    )
    contact_id: EntityID = Field(
        ..., title="Contact ID", description="The unique identifier of the contact"
    )

    attachment_id: Optional[EntityID] = Field(
        default=None,
        title="Attachment ID",
        description="The unique identifier of the attachment",
    )


class ChangedAttributes(BaseModel):
    previous_value: JsonField = Field(
        default_factory=dict,
        title="Previous Value",
        description="The previous value of the attribute",
    )
    current_value: JsonField = Field(default_factory=dict, title="Current Value")


class ContactUpdatedEvent(Event):
    account_id: EntityID = Field(
        ..., title="Account ID", description="The unique identifier of the account"
    )
    contact_id: EntityID = Field(
        ..., title="Contact ID", description="The unique identifier of the contact"
    )
    changed_attributes: Optional[dict[str, ChangedAttributes]] = Field(
        default_factory=dict,
        title="Changed Attributes",
        description="The attributes that were changed",
    )


class ContactCreatedEvent(Event):
    account_id: EntityID = Field(
        ..., title="Account ID", description="The unique identifier of the account"
    )
    contact_id: EntityID = Field(
        ..., title="Contact ID", description="The unique identifier of the contact"
    )


class WebhookEvent(Event):
    account_id: Optional[EntityID] = Field(
        default=None,
        title="Account ID",
        description="The unique identifier of the account",
    )
    contact_id: Optional[EntityID] = Field(
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
