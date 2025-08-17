import logging
from functools import cached_property
from pathlib import Path
from typing import Annotated, Any, Optional, Union

from pydantic import (
    AmqpDsn,
    BaseModel,
    BeforeValidator,
    Field,
    KafkaDsn,
    MongoDsn,
    PostgresDsn,
    RedisDsn,
    field_validator,
    model_validator,
)
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)
from pytz import timezone as tz
from urllib3.util import parse_url

PathField = Annotated[Path, BeforeValidator(lambda x: Path(x))]

BooleanField = Annotated[
    bool, BeforeValidator(lambda x: str(x) == "1" or str(x).lower() == "true")
]

BrokerDsn = Union[AmqpDsn, RedisDsn, KafkaDsn]
base_model_config = {
    "env_file": ".env",
    "env_file_encoding": "utf-8",
    "extra": "ignore",
    "validate_assignment": True,
    "case_sensitive": False,
}


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(
        **base_model_config,
        env_prefix="redis_",
        cli_prefix="redis_",
    )
    url: str = Field(
        default="redis://localhost:6379",
        title="Redis URL",
    )

    @property
    def dsn(self) -> RedisDsn:
        return RedisDsn(self.url)


class MongoSettings(BaseSettings):
    model_config = SettingsConfigDict(
        **base_model_config,
        env_prefix="mongo_",
        cli_prefix="mongo_",
    )
    url: str = Field(
        default="mongodb://localhost:27017/staging",
        description="MongoDB URL",
    )
    db_name: str = Field(default="staging", description="MongoDB database name")
    index_dimensions: int = Field(default=3072, description="The index dimensions")

    @cached_property
    def dsn(self) -> MongoDsn:
        return MongoDsn(self.url)


class PostgresSettings(BaseSettings):
    model_config = SettingsConfigDict(
        **base_model_config,
        env_prefix="postgres_",
        cli_prefix="postgres_",
    )
    url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/postgres",
        description="Postgres URL",
    )

    use_ssl: BooleanField = Field(default=False, description="Use SSL")

    migrations_dir: Optional[PathField] = Field(
        default=None,
        title="Migration directory",
        description="The directory for database migrations",
    )

    timeout: Optional[float]  = Field(
        default=60,
        title="Timeout",
        description="The timeout for database operations in seconds",
    )

    @property
    def migrations_dir_path(self) -> Path:

        return Path(self.migrations_dir).resolve() if self.migrations_dir else Path.cwd() / "migrations"

    @cached_property
    def dsn(self) -> PostgresDsn:
        return PostgresDsn(self.url)

    @model_validator(mode="before")
    @classmethod
    def validate_before(cls, data: Any) -> dict[str, Any]:
        data = data.model_dump() if isinstance(data, BaseModel) else data
        url = data.get(
            "url",
            data.get("URL", data.get("postgres_url", data.get("POSTGRES_URL", None)))
            or None,
        )
        if not url:
            return {}
        if "schema" in url:
            url = str(url).replace("?schema=public", "").replace("&schema=public", "")

        use_ssl = "sslmode=require" in url
        if use_ssl:
            url = url.replace("sslmode=require", "")

        return {
            "url": url,
            "use_ssl": use_ssl,
        }


class QdrantSettings(BaseSettings):
    model_config = SettingsConfigDict(
        **base_model_config,
        env_prefix="qdrant_",
        cli_prefix="qdrant_",
    )
    url: str = Field(
        default="http://127.0.0.1:6334",
        title="QDrant URL",
        description="The QDrant URL, e.g., http://localhost:6333 or http://localhost:6334",
    )

    port: int = Field(
        default=6333,
        title="Port",
        description="The port for the QDrant server, e.g., 6333 or 6334",
    )

    grpc_port: int = Field(
        default=6334,
        title="GrpcPort",
        description="The gRPC port for the QDrant server, e.g., 6334",
    )

    prefer_grpc: BooleanField = Field(
        default=True,
        title="Prefer GRPC mode",
        description="If true, the QDrant server will use prefer GRPC mode.",
    )
    default_vector_size: int = Field(
        default=768,
        title="Vector Size",
        description="The size of the vectors in the vector store",
    )

    @cached_property
    def host(self) -> str:
        return parse_url(self.url).host or "127.0.0.1"


class BrokerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        **base_model_config,
        env_prefix="broker_",
        cli_prefix="broker_",
    )

    url: Optional[str] = Field(
        default=None,
        title="Broker URL",
        description="RabbitMQ Or Kafka Or Redis URL",
    )

    vhost: str = Field(
        default="/",
        title="Virtual Host",
        description="The RabbitMQ virtual host to use for the connection",
    )
    use_ssl: BooleanField = Field(
        default=False,
        description="Use SSL",
    )
    cafile: Optional[PathField] = Field(
        default=None,
        title="CA File",
        description="CA file path",
    )
    certfile: Optional[PathField] = Field(
        default=None,
        title="Cert File",
        description="Cert file path",
    )
    keyfile: Optional[PathField] = Field(
        default=None,
        title="Key File",
        description="Key file path",
    )
    cert_password: Optional[str] = Field(
        default=None, title="Cert Password", description="Certificate password (if any)"
    )

    @property
    def dsn(self) -> BrokerDsn:
        return (
            RedisDsn(self.url)
            if self.is_redis
            else AmqpDsn(self.url)
            if self.is_rabbitmq
            else KafkaDsn(self.url)
        )

    @property
    def is_rabbitmq(self) -> bool:
        return self.url and "amqp" in self.url

    @property
    def is_redis(self) -> bool:
        return self.url and "redis" in self.url

    @property
    def is_kafka(self) -> bool:
        return self.url and not (self.is_rabbitmq or self.is_redis)


class KubernetesSettings(BaseSettings):
    model_config = SettingsConfigDict(
        **base_model_config,
        env_prefix="kube_",
        cli_prefix="kube_",
    )

    pod_name: Optional[str] = Field(default=None, title="Pod name")

    public_ip: Optional[str] = Field(default=None, title="Public IP")

    @field_validator("pod_name", mode="before")
    @classmethod
    def validate_pod_name(cls, value: Optional[str]) -> str:
        if not value:
            from ..utils import Crypto

            value = f"pod-{Crypto.uuid7()}"

        return value


class LLMSettings(BaseSettings):
    model_config = SettingsConfigDict(
        **base_model_config,
        env_prefix="llm_",
        cli_prefix="llm_",
        title="LLM Settings",
    )
    model_name: str = Field(
        default="llama3:8b", description="The LLM model to use"
    )

    api_url: str = Field(
        default="http://localhost:11434/api/generate", description="The LLM API URL"
    )

    api_token: str = Field(default_factory=str, title="The LLM API token", description="The LLM API token")

class Settings(BaseSettings):
    model_config = SettingsConfigDict(**base_model_config)
    env: str = Field(
        default="dev", title="The environment", description="The environment"
    )

    base_dir: PathField = Field(
        default_factory=Path.cwd, description="The base directory"
    )

    debug: BooleanField = Field(default=False, description="Debug mode")

    timezone_name: str = Field(
        default="Asia/Tel_Aviv", description="The app timezone", alias="timezone"
    )

    @property
    def timezone(self) -> tz:
        return tz(self.timezone_name)

    broker: BrokerSettings = BrokerSettings()
    redis: RedisSettings = RedisSettings()
    mongo: MongoSettings = MongoSettings()
    postgres: PostgresSettings = PostgresSettings()
    kube: KubernetesSettings = KubernetesSettings()
    qdrant: QdrantSettings = QdrantSettings()
    llm: LLMSettings = LLMSettings()

    @property
    def is_dev(self) -> bool:
        return "dev" in self.env.lower()

    @property
    def is_prod(self) -> bool:
        return "prod" in self.env.lower()

    @property
    def is_test(self) -> bool:
        return "test" in self.env.lower()

    @property
    def is_staging(self) -> bool:
        return "staging" in self.env.lower()

    @property
    def static_dir(self) -> Path:
        return self.base_dir / "static"

    @property
    def log_level(self) -> int:
        return logging.DEBUG if self.is_dev or self.debug else logging.INFO


settings: Settings = Settings()  # noqa
