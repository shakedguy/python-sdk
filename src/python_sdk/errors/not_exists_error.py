from typing import Any


class NotExistsError(Exception):
    """
    Exception raised when an entity does not exist in the database.
    """

    def __init__(self, entity_name: str, pk: Any):
        from ..utils.strings import to_singular

        """
        Initializes a new instance of the NotExistsError class.

        Args:
            entity_name (str): The name of the entity that does not exist.
            pk (Any): The ID of the entity that does not exist.
        """
        super().__init__(
            f"{to_singular(entity_name).title()} with ID '{pk}' does not exist."
        )
