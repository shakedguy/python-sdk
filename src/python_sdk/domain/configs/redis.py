from __future__ import annotations

from functools import cached_property
from typing import Annotated, Any, Mapping, Optional, Self, Union

from faststream.security import BaseSecurity
from pydantic import (
    BeforeValidator,
    Field,
    RedisDsn,
    computed_field,
    field_validator,
    model_validator,
)

from ...conf.app_settings import settings
from ...utils import Crypto, Strings
from ..base.base_model import BaseModel, base_validate_before

_URLField: Optional[str] = Annotated[
    Optional[Union[str, RedisDsn]],
    BeforeValidator(lambda x: x.unicode_string() if isinstance(x, RedisDsn) else x),
]


class RedisConfigs(BaseModel):
    url: _URLField = Field(
        default=None,
        title="URL",
        description="Redis connection URL",
    )
    host: Optional[str] = Field(
        default=None,
        title="Host",
        description="RabbitMQ host",
    )
    port: Optional[int] = Field(default=None, title="Port", description="RabbitMQ port")
    username: Optional[str] = Field(
        default=None, title="Username", description="RabbitMQ username"
    )
    password: Optional[str] = Field(
        default=None, title="Password", description="RabbitMQ password"
    )
    use_ssl: Optional[bool] = Field(
        default=settings.broker.use_ssl,
        title="Use SSL",
        description="Use SSL for the connection",
    )
    db: Optional[Union[str, int]] = Field(
        default=0, title="Database", description="Redis database number"
    )

    client_name: Optional[str] = Field(
        default=None,
        title="Client Name",
        description="Name of the Redis client connection",
    )
    health_check_interval: float = Field(
        default=15.0,
        title="Health Check Interval",
    )
    max_connections: Optional[int] = Field(
        default=5,
        title="Max Connections",
        description="Maximum number of connections to Redis",
    )
    socket_timeout: Optional[float] = Field(default=10.0, title="Socket Timeout")
    socket_connect_timeout: Optional[float] = Field(
        default=10.0, title="Socket Connect Timeout"
    )
    socket_read_size: int = Field(default=65536, title="Socket Read Size")
    socket_keepalive: bool = Field(default=True, title="Socket Keepalive")
    socket_keepalive_options: Optional[Mapping[int, int | bytes]] = Field(
        default=None, title="Socket Keepalive Options"
    )
    retry_on_timeout: bool = Field(default=True, title="Retry on Timeout")

    @field_validator("client_name", mode="before")
    @classmethod
    def validate_connection_name(cls, value: Optional[str]) -> str:
        return f"{Strings.slugify(value or 'buzzerpy')}:{Crypto.generate_random_id(8, encoding='hex', case='upper')}"

    @cached_property
    def dsn(self) -> RedisDsn:
        """Return the Redis connection URL as an RedisDsn."""

        url = self.url or str(
            "redis://{username}:{password}@{self.host}:{port}/{db}".format(
                username=self.username or "default",
                password=self.password or "",
                self=self,
                port=self.port or (5671 if self.use_ssl else 5672),
                db=self.db or 0,
            )
        )

        return RedisDsn(url)

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

    @model_validator(mode="before")  # noqa
    @classmethod
    def before_validator(cls, value: Any) -> Any:
        if isinstance(value, dict):
            value = base_validate_before(value)
            if not value.get("host", None) and settings.broker.is_rabbitmq:
                value.setdefault("url", settings.broker.url)
            value.setdefault("use_ssl", settings.broker.use_ssl)

        return value

    @model_validator(mode="after")
    def validate_after(self) -> Self:
        if not any([self.url, self.host]):
            raise ValueError("Either 'url' or 'host' must be provided.")

        if self.use_ssl:
            self.client_properties.auth = "EXTERNAL"

        return self
