class NoIdError(Exception):
    """
    Exception raised when an entity does not have an ID value set when it is required.
    for example, when updating an entity, when trying to reference an entity, etc.
    """

    def __init__(self, entity_name: str) -> None:
        """
        Initializes a new instance of the NoIdError class.

        Args:
            entity_name (str): The name of the entity that does not have an ID value set.
        """

        from ..utils import Strings

        super().__init__(
            f"{Strings.to_singular(entity_name).title()} does not have an ID value set."
        )
