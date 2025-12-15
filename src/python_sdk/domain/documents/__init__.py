
import importlib.util

if importlib.util.find_spec("pymongo") is not None:
    from ._documents import (
        BaseDocument,
        DocumentIndex,
        DocumentIndexType,
    )
    from .mongo import (
        MongoDocument,
        MongoDocumentTimeStampedModel,
        MongoDocumentTimeStampedVersionedModel,
        MongoDocumentVersionModel,
        MongoView,
    )

if importlib.util.find_spec("qdrant_client") is not None:
    from .qdrant import QdrantDocument, QdrantTimeStampedDocument
