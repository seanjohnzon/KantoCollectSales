"""
Inventory API tests (separate inventory database).
"""

from collections.abc import Generator
from typing import Callable

import pytest
from sqlmodel import SQLModel, Session, create_engine

from app.core.inventory_database import get_inventory_db
from app.main import app


@pytest.fixture
def inventory_session(tmp_path) -> Generator[Session, None, None]:
    """
    Provide a fresh inventory database session for each test.
    """
    engine = create_engine(f"sqlite:///{tmp_path/'inventory_test.db'}")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def override_inventory_db(inventory_session: Session) -> Generator[Callable[[], Generator[Session, None, None]], None, None]:
    """
    Override inventory DB dependency for tests.
    """
    def _override() -> Generator[Session, None, None]:
        yield inventory_session
    app.dependency_overrides[get_inventory_db] = _override
    yield _override
    app.dependency_overrides.pop(get_inventory_db, None)


@pytest.mark.asyncio
async def test_inventory_crud(client, admin_token, override_inventory_db):
    """
    Expected: create master card, add inventory item, list items.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    card_payload = {
        "card_number": "OP01-001",
        "name": "Monkey.D.Luffy",
        "set_code": "OP-01",
        "variant": "Base",
    }
    card_res = await client.post("/api/v1/admin/inventory/cards", json=card_payload, headers=headers)
    assert card_res.status_code == 201
    card_id = card_res.json()["id"]

    item_payload = {"master_card_id": card_id, "quantity": 2}
    item_res = await client.post("/api/v1/admin/inventory/", json=item_payload, headers=headers)
    assert item_res.status_code == 201
    item_data = item_res.json()
    assert item_data["quantity"] == 2
    assert item_data["card"]["card_number"] == "OP01-001"

    list_res = await client.get("/api/v1/admin/inventory/", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1


@pytest.mark.asyncio
async def test_inventory_invalid_card(client, admin_token, override_inventory_db):
    """
    Failure: creating inventory item with unknown master_card_id returns 404.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    item_payload = {"master_card_id": 9999, "quantity": 1}
    res = await client.post("/api/v1/admin/inventory/", json=item_payload, headers=headers)
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_inventory_search(client, admin_token, override_inventory_db):
    """
    Edge: searching master cards returns matching card.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    await client.post(
        "/api/v1/admin/inventory/cards",
        json={"card_number": "OP02-001", "name": "Roronoa Zoro", "set_code": "OP-02"},
        headers=headers,
    )

    search_res = await client.get("/api/v1/admin/inventory/cards?search=Zoro", headers=headers)
    assert search_res.status_code == 200
    assert len(search_res.json()) == 1
