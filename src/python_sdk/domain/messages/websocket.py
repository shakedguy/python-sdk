from __future__ import annotations

from typing import Any, Literal, Optional, Union

from pydantic import Field, model_validator

from ...utils import Crypto, Strings
from ..base.base_model import BaseModel, base_validate_before
from ..base.fields import EntityIDField, UUIDField


class NewConversationRequestData(BaseModel):
    exchange: Optional[str] = Field(default_factory=str, title="The exchange name")
    phone_number: str = Field(default_factory=str, title="The phone number")


class NewConversationRequest(BaseModel):
    cmd: Literal["new_conversation"]
    data: NewConversationRequestData = Field(..., title="The exchange name")


class NewMessageRequestData(BaseModel):
    exchange: Optional[str] = Field(default_factory=str, title="The exchange name")
    phone_number: str = Field(default_factory=str, title="The phone number")
    conversation_id: Union[str, int] = Field(
        default_factory=str, title="The conversation ID"
    )
    prompt: str = Field(default_factory=str, title="The message prompt")
    speaker_id: Optional[str] = Field(default_factory=str, title="The speaker ID")
    gender: Optional[Literal["male", "female"]] = Field(
        default=None, title="The gender", description="The gender of the user"
    )


class NewMessageRequest(BaseModel):
    cmd: Literal["new_message"]
    data: NewMessageRequestData = Field(..., title="The exchange name")


class RequestEvent(BaseModel):
    id: Optional[UUIDField] = Field(
        default_factory=Crypto.uuidv7, title="The unique identifier of the event"
    )
    type: Literal["req"]
    agent: Optional[str] = Field(default_factory=str, title="The agent of the event")
    data: Union[NewConversationRequest, NewMessageRequest] = Field(discriminator="cmd")
    account_id: Optional[EntityIDField] = Field(default=None, title="Account ID")
    inbox_id: Optional[EntityIDField] = Field(default=None, title="Inbox ID")

    @property
    def is_new_conversation_request(self) -> bool:
        return isinstance(self.data, NewConversationRequest)

    @property
    def is_new_message_request(self) -> bool:
        return isinstance(self.data, NewMessageRequest)

    @property
    def is_valid(self) -> bool:
        return all([self.type, self.agent, self.account_id, self.inbox_id, self.data])

    @property
    def errors(self) -> list[str]:
        res = []
        if not self.type:
            res.append("Missing request type.")
        if "req" not in self.type:
            res.append("Invalid request type.")
        if not self.agent:
            res.append("Missing agent name.")
        if not self.account_id:
            res.append("Missing account ID.")
        if not self.inbox_id:
            res.append("Missing inbox ID.")
        if not self.data:
            res.append("Missing data.")
        return res


class PingEvent(BaseModel):
    type: Literal["ping"]
    data: Optional[Union[str, dict[str, Any]]] = Field(
        default=None, title="The data of the event"
    )


class PongEvent(BaseModel):
    type: Literal["pong"]
    data: Optional[Union[str, dict[str, Any]]] = Field(
        default=None, title="The data of the event"
    )


class ResponseDataData(BaseModel):
    exchange: Optional[str] = Field(default_factory=str, title="The exchange name")
    phone_number: str = Field(default_factory=str, title="The phone number")
    conversation_id: Union[str, int] = Field(
        default_factory=str, title="The conversation ID"
    )
    prompt: Optional[str] = Field(default_factory=str, title="The message prompt")
    speaker_id: Optional[str] = Field(default_factory=str, title="The speaker ID")
    response: Optional[str] = Field(default=None, title="The response of the event")

    @model_validator(mode="before")
    @classmethod
    def validate(cls, data: Any) -> dict[str, Any]:
        res = data.model_dump() if isinstance(data, BaseModel) else dict(data)
        res = dict(res)

        res["phone_number"] = Strings.format_phone_number(res.get("phone_number", ""))
        res["exchange"] = Strings.format_phone_number(res.get("exchange", ""))

        return res


class ResponseData(BaseModel):
    cmd: Literal["new_conversation", "new_message"]
    data: Optional[ResponseDataData] = Field(default=None, title="The data")
    success: bool = Field(default=True, title="The success status of the response")
    error_str: Optional[str] = Field(
        default=None,
        title="The error message of the response",
    )


class ResponseEvent(BaseModel):
    id: Optional[UUIDField] = Field(
        default_factory=Crypto.uuidv7, title="The unique identifier of the event"
    )
    type: Literal["res"]
    agent: Optional[str] = Field(default_factory=str, title="The agent of the event")
    data: Optional[ResponseData] = Field(default=None, title="Data of the event")
    account_id: Optional[EntityIDField] = Field(default=None, title="Account ID")
    inbox_id: Optional[EntityIDField] = Field(default=None, title="Inbox ID")


class SocketEvent(BaseModel):
    event: Union[PingEvent, RequestEvent, PongEvent, ResponseEvent] = Field(
        discriminator="type"
    )

    @model_validator(mode="before")
    @classmethod
    def on_before(cls, value: Any) -> Any:
        value = base_validate_before(value)
        if "event" not in value:
            value = {"event": value}

        return value

    @property
    def is_ping(self) -> bool:
        return isinstance(self.event, PingEvent)

    @property
    def is_pong(self) -> bool:
        return isinstance(self.event, PongEvent)

    @property
    def is_request(self) -> bool:
        return isinstance(self.event, RequestEvent)

    @property
    def is_response(self) -> bool:
        return isinstance(self.event, ResponseEvent)

    @staticmethod
    def build_success_event(
        req: RequestEvent,
        conversation_id: Union[str, int],
        response: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> ResponseEvent:
        """Build a success event with the agent's response."""

        return ResponseEvent(
            id=req.id,
            type="res",
            agent=req.agent,
            account_id=req.account_id,
            inbox_id=req.inbox_id,
            data=ResponseData(
                cmd=req.data.cmd,
                success=True,
                data=ResponseDataData(
                    phone_number=req.data.data.phone_number,
                    exchange=req.data.data.exchange,
                    conversation_id=conversation_id,
                    prompt=prompt,
                    response=response,
                ),
            ),
        )

    @staticmethod
    def build_error_event(
        req: RequestEvent,
        conversation_id: Optional[str] = None,
        prompt: Optional[str] = None,
        error_str: Optional[str] = None,
    ) -> ResponseEvent:
        """Build an error event when conversation ID or prompt is missing."""
        error_str = error_str or (
            "missing conversation id and prompt"
            if not conversation_id and not prompt
            else "missing conversation id"
            if not conversation_id
            else "missing prompt"
        )
        return ResponseEvent(
            id=req.id,
            type="res",
            data=ResponseData(
                cmd=req.data.cmd,
                success=False,
                error_str=error_str,
                data=ResponseDataData(
                    phone_number=req.data.data.phone_number,
                    exchange=req.data.data.exchange,
                    conversation_id=conversation_id,
                    prompt=prompt,
                    response=None,
                ),
            ),
        )
