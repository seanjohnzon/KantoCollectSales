"""
WhatNot sales database configuration (separate from core and inventory DBs).

Uses SQLModel with a sync engine for sales data management.
"""

from collections.abc import Generator

from sqlmodel import SQLModel, Session, create_engine

from .config import settings


whatnot_engine = create_engine(
    settings.whatnot_database_url,
    echo=settings.debug,
)


def init_whatnot_db() -> None:
    """
    Initialize the WhatNot sales database by creating tables.
    """
    SQLModel.metadata.create_all(whatnot_engine)


def get_whatnot_db() -> Generator[Session, None, None]:
    """
    Provide a sync session for WhatNot sales operations.

    Yields:
        Session: SQLModel session for whatnot sales database.
    """
    with Session(whatnot_engine) as session:
        yield session
