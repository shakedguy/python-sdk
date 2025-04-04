from pathlib import Path
from typing import Annotated, Any, Optional

from pydantic import (
    AmqpDsn,
    BaseModel,
    BeforeValidator,
    Field,
    MongoDsn,
    PostgresDsn,
    RedisDsn,
    model_validator,
)
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)
from pytz import timezone as tz

PathField = Annotated[Path, BeforeValidator(lambda x: Path(x))]

BooleanField = Annotated[
    bool, BeforeValidator(lambda x: str(x) == "1" or str(x).lower() == "true")
]
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

    @property
    def dsn(self) -> MongoDsn:
        return MongoDsn(self.url)


class PostgresSettings(BaseSettings):
    model_config = SettingsConfigDict(
        **base_model_config,
        env_prefix="postgres_",
        cli_prefix="postgres_",
    )
    url: str = Field(
        default="postgresql://localhost:5432/chatwoot_dev",
        description="Postgres URL",
    )

    use_ssl: BooleanField = Field(default=False, description="Use SSL")

    @property
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


class RabbitMQSettings(BaseSettings):
    model_config = SettingsConfigDict(
        **base_model_config,
        env_prefix="rabbitmq_",
        cli_prefix="rabbitmq_",
    )

    url: str = Field(
        default="amqp://guest:guest@localhost:5672/",
        description="RabbitMQ URL",
    )

    virtual_host: str = Field(
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
    def dsn(self) -> AmqpDsn:
        return AmqpDsn(self.url)


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

    rabbit_mq: RabbitMQSettings = RabbitMQSettings()
    redis: RedisSettings = RedisSettings()
    mongo: MongoSettings = MongoSettings()
    postgres: PostgresSettings = PostgresSettings()

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


settings: Settings = Settings()  # noqa
