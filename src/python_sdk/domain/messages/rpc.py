from __future__ import annotations

from typing import Literal, Optional

from pydantic import Field

from ..base.fields import EntityIDField
from .base import BaseMessage, BaseMessageBody


class CreateConversationMessageBody(BaseMessageBody):
    """
    RPC message to create a conversation.
    This message is used to create a new conversation in the system.

    Attributes:
        id (UUIDField): The unique identifier of the message.
        account_id (EntityIDField): The ID of the account.
        inbox_id (EntityIDField): The ID of the inbox.
        phone_number (str): The phone number of the contact.
        message (Optional[str]): The message to send.
        cw_integration (Optional[bool]): Whether the conversation should be in chatwoot or not.
        timestamp: (DateTimeField): The time when the message was created.
    """

    account_id: EntityIDField = Field(
        ..., title="Account ID", description="The ID of the account"
    )

    inbox_id: EntityIDField = Field(
        ..., title="Inbox ID", description="The ID of the inbox"
    )

    contact_id: Optional[EntityIDField] = Field(
        default=None, title="Contact ID", description="The ID of the contact"
    )

    phone_number: str = Field(
        ..., title="Contact Phone Number", description="The phone number of the contact"
    )

    message: Optional[str] = Field(
        default=None, title="Message", description="The message to send"
    )
    message_type: Optional[Literal["incoming", "outgoing"]] = Field(
        default=None, title="Message Type", description="The message type"
    )

    cw_integration: Optional[bool] = Field(
        default=False,
        title="Chatwoot Integration",
        description="Whether the conversation should be in chatwoot or not",
    )


class CreateConversationMessage(BaseMessage[CreateConversationMessageBody]):
    """
    RPC message to create a conversation.
    This message is used to create a new conversation in the system.

    Attributes:
        id (UUIDField): The unique identifier of the message.
        pattern (str): The pattern of the message.
        data: (CreateConversationMessageBody): The data of the message.
        timestamp: (DateTimeField): The time when the message was created.
    """

    pattern: str = "conversations.create"
    data: CreateConversationMessageBody = Field(
        ..., title="Data", description="Message data"
    )


class CreateConversationResponseMessage(CreateConversationMessageBody):
    """
    RPC message to create a conversation response.
    This message is used to respond to a request to create a new conversation in the system.

    Attributes:
        id (UUIDField): The unique identifier of the message.
        account_id (EntityIDField): The ID of the account.
        inbox_id (EntityIDField): The ID of the inbox.
        phone_number (str): The phone number of the contact.
        conversation_id (EntityIDField): The ID of the conversation.
        message (Optional[str]): The message to send.
        timestamp: (DateTimeField): The time when the message was created.

    """

    conversation_id: EntityIDField = Field(
        ..., title="Conversation ID", description="The ID of the conversation"
    )


class AskAIMessage(BaseMessage):
    """
    RPC message to ask AI a question.
    This message is used to ask AI a question and get a response.

    Attributes:
        id (UUIDField): The unique identifier of the message.
        account_id (EntityIDField): The ID of the account.
        inbox_id (EntityIDField): The ID of the inbox.
        prompt (str): The prompt to ask AI.
        cw_integration (Optional[bool]): Whether the conversation should be in chatwoot or not.
        timestamp: (DateTimeField): The time when the message was created.
    """

    account_id: EntityIDField = Field(
        ..., title="Account ID", description="The ID of the account"
    )

    inbox_id: EntityIDField = Field(
        ..., title="Inbox ID", description="The ID of the inbox"
    )
    prompt: str = Field(..., title="Prompt", description="The prompt to ask AI")

    cw_integration: Optional[bool] = Field(
        default=False,
        title="Chatwoot Integration",
        description="Whether the conversation should be in chatwoot or not",
    )


class AskAIResponseMessage(AskAIMessage):
    """
    RPC message to ask AI a question response.
    This message is used to respond to a request to ask AI a question.

    Attributes:
        id (UUIDField): The unique identifier of the message.
        account_id (EntityIDField): The ID of the account.
        inbox_id (EntityIDField): The ID of the inbox.
        prompt (str): The prompt to ask AI.
        response (str): The response from AI.
        cw_integration (Optional[bool]): Whether the conversation should be in chatwoot or not.
        timestamp: (DateTimeField): The time when the message was created.
    """

    response: str = Field(..., title="Response", description="The response from AI")
