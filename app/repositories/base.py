"""Base repository class for common database operations."""

from typing import Protocol, TypeVar

from sqlalchemy.orm import Session

from app.data_access.models import Base


class HasId(Protocol):
    """Protocol for models that have an id attribute."""

    id: int


T = TypeVar("T", bound=Base)


class BaseRepository:
    """Base repository class with common CRUD operations."""

    def __init__(self, model: type[T], session: Session):
        """Initialize the repository."""
        self.model = model
        self.session = session

    def get_by_id(self, id: int) -> T | None:
        """Get an entity by ID.

        Args:
            id: The entity ID

        Returns:
            The entity or None if not found
        """
        return self.session.query(self.model).filter(self.model.id == id).first()  # type: ignore[return-value]

    def get_all(self, limit: int | None = None, offset: int = 0) -> list[T]:
        """Get all entities with optional pagination.

        Args:
            limit: Maximum number of entities to return
            offset: Number of entities to skip

        Returns:
            List of entities
        """
        query = self.session.query(self.model)
        if limit:
            query = query.limit(limit).offset(offset)
        return query.all()

    def create(self, **kwargs) -> T:
        """Create a new entity.

        Args:
            **kwargs: Entity attributes

        Returns:
            The created entity
        """
        entity = self.model(**kwargs)
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return entity

    def update(self, id: int, **kwargs) -> T | None:
        """Update an entity.

        Args:
            id: The entity ID
            **kwargs: Attributes to update

        Returns:
            The updated entity or None if not found
        """
        entity = self.get_by_id(id)
        if entity:
            for key, value in kwargs.items():
                setattr(entity, key, value)
            self.session.commit()
            self.session.refresh(entity)
        return entity

    def delete(self, id: int) -> bool:
        """Delete an entity.

        Args:
            id: The entity ID

        Returns:
            True if deleted, False if not found
        """
        entity = self.get_by_id(id)
        if entity:
            self.session.delete(entity)
            self.session.commit()
            return True
        return False

    def soft_delete(self, id: int, user_id: int | None = None) -> bool:
        """Soft delete an entity.

        Args:
            id: The entity ID
            user_id: The user performing the deletion

        Returns:
            True if deleted, False if not found
        """
        entity = self.get_by_id(id)
        if entity and hasattr(entity, "is_deleted"):
            entity.is_deleted = True
            if hasattr(entity, "deleted_at"):
                from datetime import datetime

                entity.deleted_at = datetime.utcnow()
            if hasattr(entity, "deleted_by"):
                entity.deleted_by = user_id
            self.session.commit()
            return True
        return False

    def filter_by(self, **kwargs) -> list[T]:
        """Filter entities by attributes.

        Args:
            **kwargs: Filter attributes

        Returns:
            List of entities matching the filters
        """
        return self.session.query(self.model).filter_by(**kwargs).all()

    def exists(self, **kwargs) -> bool:
        """Check if an entity exists with the given attributes.

        Args:
            **kwargs: Filter attributes

        Returns:
            True if exists, False otherwise
        """
        return self.session.query(self.model).filter_by(**kwargs).first() is not None
