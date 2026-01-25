"""
Inventory database configuration (separate from core DB).

Uses SQLModel with a sync engine for local inventory management.
"""

from collections.abc import Generator

from sqlmodel import SQLModel, Session, create_engine

from .config import settings


inventory_engine = create_engine(
    settings.inventory_database_url,
    echo=settings.debug,
)


def init_inventory_db() -> None:
    """
    Initialize the inventory database by creating tables.
    """
    SQLModel.metadata.create_all(inventory_engine)


def get_inventory_db() -> Generator[Session, None, None]:
    """
    Provide a sync session for inventory operations.

    Yields:
        Session: SQLModel session for inventory database.
    """
    with Session(inventory_engine) as session:
        yield session
