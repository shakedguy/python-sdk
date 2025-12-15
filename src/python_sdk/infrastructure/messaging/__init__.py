import importlib.util

if importlib.util.find_spec("faststream") is not None:
    from .brokers import *
    from .queues import *
    from .rpc import *
