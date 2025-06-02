from __future__ import annotations

from functools import cached_property
from typing import Annotated, Any, Literal, Optional, Union

from faststream.security import BaseSecurity
from pydantic import (
    BeforeValidator,
    Field,
    KafkaDsn,
    computed_field,
    field_validator,
    model_validator,
)

from ...conf.app_settings import settings
from ...utils import Crypto, Strings
from ..base.base_model import BaseModel, base_validate_before

_URLField: Optional[str] = Annotated[
    Optional[Union[str, KafkaDsn]],
    BeforeValidator(lambda x: x.unicode_string() if isinstance(x, KafkaDsn) else x),
]


class KafkaConfigs(BaseModel):
    bootstrap_servers: _URLField = Field(
        default=None,
        title="Bootstrap Servers",
        description="Kafka bootstrap server",
    )

    request_timeout_ms: int = (
        Field(
            default=40 * 1000,
            title="Request Timeout MS",
            description="Request timeout in milliseconds",
        ),
    )
    retry_backoff_ms: int = (
        Field(
            default=100,
            title="Retry Backoff MS",
            description="Retry backoff time in milliseconds",
        ),
    )
    metadata_max_age_ms: int = (
        Field(
            default=5 * 60 * 1000,
            title="Metadata Max Age MS",
            description="Maximum age of metadata in milliseconds",
        ),
    )
    connections_max_idle_ms: int = (
        Field(
            default=9 * 60 * 1000,
            title="Connections Max Idle MS",
            description="Maximum idle time for connections in milliseconds",
        ),
    )

    acks: Literal[0, 1, -1, "all"] = Field(
        default="all",
        title="Acks",
        description="Acknowledgment level for message delivery",
    )
    compression_type: Optional[Literal["gzip", "snappy", "lz4", "zstd"]] = Field(
        default=None,
        title="Compression Type",
        description="Compression type for messages",
    )

    max_request_size: int = Field(
        default=1024 * 1024,
        title="Max Request Size",
        description="Maximum size of a request in bytes",
    )

    graceful_timeout: Optional[float] = Field(
        default=15.0,
        title="Graceful Timeout",
        description="Graceful shutdown timeout in seconds",
    )

    use_ssl: Optional[bool] = Field(
        default=settings.broker.use_ssl,
        title="Use SSL",
        description="Use SSL",
    )

    timeout: Optional[Union[int, float]] = Field(
        default=5.0, title="Timeout", description="Connection timeout in seconds"
    )
    fail_fast: Optional[bool] = Field(
        default=True, title="Fail Fast", description="Fail fast on connection errors"
    )
    reconnect_interval: Optional[Union[int, float]] = Field(
        default=5.0,
        title="Reconnect Interval",
        description="Interval to wait before retrying connection in seconds",
    )

    channel_number: Optional[int] = Field(
        default=None, title="Channel Number", description="Channel number"
    )
    publisher_confirms: Optional[bool] = Field(
        default=False, title="Publisher Confirms", description="Publisher confirms"
    )

    max_consumers: Optional[int] = Field(
        default=5, title="Max Consumers", description="Max consumers"
    )
    client_id: Optional[str] = Field(default=None, title="App ID", description="App ID")

    log_level: Optional[int] = Field(
        default=settings.log_level,
        title="Log Level",
        description="Log level",
    )

    @computed_field
    def security(self) -> Optional[BaseSecurity]:
        from ...infrastructure.messaging.brokers.ssl import create_ssl_context

        return (
            BaseSecurity(
                ssl_context=create_ssl_context(),
                use_ssl=self.use_ssl,
            )
            if self.use_ssl
            else None
        )

    @cached_property
    def dsn(self) -> KafkaDsn:
        """Return the RabbitMQ connection URL as an instance of KafkaDsn."""

        return KafkaDsn(self.bootstrap_servers)

    @field_validator("client_id", mode="before")
    @classmethod
    def validate_client_id(cls, value: Optional[str]) -> str:
        return f"{Strings.slugify(value or 'buzzerpy')}:{Crypto.generate_random_id(8, encoding='hex', case='upper')}"

    @model_validator(mode="before")  # noqa
    @classmethod
    def before_validator(cls, value: Any) -> Any:
        if isinstance(value, dict):
            value = base_validate_before(value)
            if not value.get("host", None) and settings.broker.is_kafka:
                value.setdefault("bootstrap_servers", settings.broker.url)
            value.setdefault("use_ssl", settings.broker.use_ssl)

        return value
