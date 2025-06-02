import logging

from .api import *
from .microservices import *
from .socketio import *
from .websocket import *

logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("socketio").setLevel(logging.WARNING)
