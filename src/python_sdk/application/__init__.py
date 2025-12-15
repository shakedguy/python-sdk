import logging

from .api import *
from .websocket import *

if importlib.util.find_spec("faststream") is not None:
    from .microservices import *

if importlib.util.find_spec("socketio") is not None:
    from .socketio import *
logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("socketio").setLevel(logging.WARNING)
