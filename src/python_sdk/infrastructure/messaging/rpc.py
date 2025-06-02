from typing import Annotated, Optional, Union

from fastapi import Depends
from faststream import Depends as FaststreamDepends
from loguru import logger

from ...conf.app_settings import settings
from .brokers import Broker, BrokerUrl
from .queues import (
    HEALTH_CHECK_QUEUE_NAME,
    health_check_exchange,
)


class RPC(object):
    def __init__(self, broker: Optional[Union[Broker, BrokerUrl]] = None):
        broker = broker or settings.broker.url
        self.broker: Broker = broker if isinstance(broker, Broker) else Broker(broker)

    async def health_check(self) -> bool:
        """
        Perform a health check to ensure the RPC service is operational.
        """
        try:
            await self.broker.start()
            res = await self.broker.request(
                to=HEALTH_CHECK_QUEUE_NAME,
                exchange=health_check_exchange,
                timeout=10.0,
                message={"action": "health_check"},
            )
            return bool(res)
        except Exception as e:
            logger.error(f"Health check failed: {repr(e)}")
            return False


RPCFastApiDep = Annotated[RPC, Depends(lambda: RPC())]
RPCFastStreamDep = Annotated[RPC, FaststreamDepends(lambda: RPC())]
