from pydantic import Field

from ....orm.models import BaseModel, DateTimeField, UUIDField


class Event(BaseModel):
    id: UUIDField = Field(
        ..., title="Message ID", description="The unique identifier of the message"
    )
    timestamp: DateTimeField = Field(
        ..., title="Timestamp", description="The time when the message was created"
    )
