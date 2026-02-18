"""Custom exceptions for the Data Access service."""


class EntityNotFoundError(Exception):
    """Raised when an entity with the given ID does not exist."""

    def __init__(self, entity_type: str, entity_id: str):
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(f"{entity_type} with id '{entity_id}' not found")


class ForeignKeyError(Exception):
    """Raised when a foreign key reference is invalid."""

    def __init__(self, field: str, value: str):
        self.field = field
        self.value = value
        super().__init__(f"Referenced {field} '{value}' does not exist")
