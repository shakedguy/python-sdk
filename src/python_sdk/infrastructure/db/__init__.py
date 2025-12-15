import importlib.util

if importlib.util.find_spec("pymongo") is not None:
    from .mongo import Mongo, MongoClients, MongoCollection

if importlib.util.find_spec("psycopg") is not None:
    from .postgres import Postgres, PostgresConnectionPool

if importlib.util.find_spec("qdrant_client") is not None:
    from .qdrant import Qdrant
