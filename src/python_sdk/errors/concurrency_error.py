from typing import Any


class ConcurrencyError(Exception):
    """
    Exception raised when a concurrency error occurs.
    """

    def __init__(self, collection_name: str, pk: Any):
        from ..utils import Strings

        """
        Initializes a new instance of the ConcurrencyError class.

        Args:
            collection_name (str): The name of the collection.
            pk (str): The primary key of the record.
        """
        super().__init__(
            f"{Strings.to_singular(collection_name).title()} with ID '{pk}' was updated or deleted by another transaction."
        )
