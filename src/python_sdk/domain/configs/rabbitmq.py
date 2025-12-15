from __future__ import annotations

from functools import cached_property
from typing import Annotated, Any, Literal, Optional, Self, Union

from faststream.security import BaseSecurity
from pydantic import (
    AmqpDsn,
    BeforeValidator,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

from ...conf.app_settings import settings
from ...utils.crypto import generate_random_id
from ...utils.strings import slugify
from ..base.base_model import BaseModel, base_validate_before

_URLField: Optional[str] = Annotated[
    Optional[Union[str, AmqpDsn]],
    BeforeValidator(lambda x: x.unicode_string() if isinstance(x, AmqpDsn) else x),
]


class RabbitMQConfigs(BaseModel):
    url: _URLField = Field(
        default=None,
        title="URL",
        description="RabbitMQ connection URL",
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

    virtualhost: Optional[str] = Field(
        default=settings.broker.vhost,
        title="Virtual Host",
        description="RabbitMQ virtual host to use for the connection",
    )
    use_ssl: Optional[bool] = Field(
        default=settings.broker.use_ssl,
        title="Use SSL",
        description="Use SSL",
    )
    client_properties: Optional[Union[RabbitClientProperties, dict]] = Field(
        default_factory=lambda: RabbitClientProperties(),
        title="Client Properties",
        description="RabbitMQ client properties for the connection",
    )
    timeout: Optional[Union[int, float]] = Field(
        default=5.0, title="Timeout", description="Connection timeout in seconds"
    )
    fail_fast: Optional[bool] = Field(
        default=False, title="Fail Fast", description="Fail fast on connection errors"
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
    app_id: Optional[str] = Field(default=None, title="App ID", description="App ID")
    graceful_timeout: Optional[float] = Field(
        default=5.0,
        title="Graceful Timeout",
        description="Graceful shutdown timeout in seconds",
    )

    log_level: Optional[int] = Field(
        default=settings.log_level,
        title="Log Level",
        description="Log level",
    )

    @computed_field
    def security(self) -> Optional[BaseSecurity]:
        from ...infrastructure.messaging.brokers.ssl import create_ssl_context

        use_ssl = self.use_ssl or self.url and self.url.startswith("amqps://")
        return (
            BaseSecurity(
                ssl_context=create_ssl_context(),
                use_ssl=use_ssl,
            )
            if use_ssl
            else None
        )

    @cached_property
    def dsn(self) -> AmqpDsn:
        """Return the RabbitMQ connection URL as an AmqpDsn."""

        url = self.url or str(
            "{protocol}://{username}:{password}@{self.host}:{port}/{virtual_host}".format(
                protocol="amqps" if self.use_ssl else "amqp",
                username=self.username or "guest",
                password=self.password or "guest",
                self=self,
                port=self.port or (5671 if self.use_ssl else 5672),
                virtual_host=(
                    self.virtualhost[1:]
                    if self.virtualhost and self.virtualhost.startswith("/")
                    else self.virtualhost
                ),
            )
        )

        return AmqpDsn(url)

    @cached_property
    def connection_args(self) -> dict[str, Any]:
        res = self.model_dump(
            exclude={"username", "password", "use_ssl", "url", "host", "port"}
        )
        if self.use_ssl:
            res["host"] = self.dsn.host
            res["port"] = self.dsn.port
        else:
            res["url"] = self.dsn.unicode_string()
        return res

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


class RabbitClientProperties(BaseModel):
    connection_name: Optional[str] = Field(
        default=None, title="Connection Name", description="Connection name"
    )
    heartbeat: Optional[int] = Field(
        default=60, title="Heartbeat", description="Heartbeat interval in seconds"
    )
    connection_timeout: Optional[int] = Field(
        default=10,
        title="Connection Timeout",
        description="Connection timeout in seconds",
    )
    channel_max: Optional[int] = Field(
        default=5,
        title="Channel Max",
        description="Maximum number of channels allowed per connection",
    )
    auth: Literal["AMQPLAIN", "PLAIN", "EXTERNAL"] = Field(
        default="PLAIN",
        title="Auth",
        description="Authentication mechanism to use",
    )

    @field_validator("connection_name", mode="before")
    @classmethod
    def validate_connection_name(cls, value: Optional[str]) -> str:
        return f"{slugify(value or 'buzzerpy')}:{generate_random_id(8, encoding='hex', case='upper')}"
