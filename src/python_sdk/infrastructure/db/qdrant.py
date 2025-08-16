from contextlib import AbstractContextManager
from typing import Optional

from qdrant_client import AsyncQdrantClient, QdrantClient

from ...conf.app_settings import settings


class Qdrant(AbstractContextManager):
    __slots__ = (
        "sync_client",
        "async_client",
    )

    def __init__(
            self,
            host: Optional[str] = None,
            port: Optional[int] = None,
            grpc_port: Optional[int] = None,
            prefer_grpc: Optional[bool] = None,
    ) -> None:
        """
        Context manager for Qdrant client.
        Initializes the Qdrant client with the provided parameters or from settings.
        If no parameters are provided, it uses the settings from the application configuration.
        Args:
            host (Optional[str]): The host of the Qdrant server. Defaults to settings.qdrant.host.
            port (Optional[int]): The port of the Qdrant server. Defaults to settings.qdrant.port.
            grpc_port (Optional[int]): The gRPC port of the Qdrant server. Defaults
            to settings.qdrant.grpc_port.
            prefer_grpc (Optional[bool]): Whether to prefer gRPC for communication.
        Returns:
            None
        """
        kwargs = {
            "host": host or settings.qdrant.host,
            "port": port or settings.qdrant.port,
            "grpc_port": grpc_port or settings.qdrant.grpc_port,
            "prefer_grpc": prefer_grpc if prefer_grpc is not None else settings.qdrant.prefer_grpc,
        }
        self.sync_client: QdrantClient = QdrantClient(**kwargs)
        self.async_client: AsyncQdrantClient = AsyncQdrantClient(**kwargs)

    def __enter__(self) -> QdrantClient:

        return self.sync_client

    async def __aenter__(self) -> AsyncQdrantClient:
        return self.async_client

    def __exit__(self, exc_type, exc_val, exc_tb):

        if self.sync_client:
            self.sync_client.close()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.async_client:
            await self.async_client.close()
