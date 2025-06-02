import ssl
from functools import cache
from ssl import SSLContext

from faststream.rabbit import RabbitBroker as RB  # noqa

from ....conf.app_settings import settings


@cache
def create_ssl_context() -> SSLContext:
    context = ssl.create_default_context(
        ssl.Purpose.SERVER_AUTH,
        cafile=settings.broker.cafile,
    )

    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    context.load_cert_chain(
        certfile=settings.broker.certfile,
        keyfile=settings.broker.keyfile,
        password=settings.broker.cert_password,
    )

    return context
