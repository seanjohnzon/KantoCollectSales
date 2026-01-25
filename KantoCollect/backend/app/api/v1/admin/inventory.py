"""
Inventory management endpoints (One Piece products first).

Uses a separate inventory database to avoid mixing with core data.
"""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlmodel import Session, select

from app.api.deps import AdminUser
from app.core.inventory_database import get_inventory_db
from app.models.inventory import (
    MasterCard,
    InventoryItem,
    MasterCardCreate,
    MasterCardRead,
    InventoryItemCreate,
    InventoryItemRead,
    InventoryStatus,
    ImportResult,
)
from app.services.inventory import import_from_excel

router = APIRouter()


def _to_master_card_read(card: MasterCard) -> MasterCardRead:
    """
    Convert MasterCard model to read schema.
    """
    return MasterCardRead.model_validate(card)


def _to_inventory_read(item: InventoryItem, card: Optional[MasterCard]) -> InventoryItemRead:
    """
    Convert inventory item and card to read schema.
    """
    payload = InventoryItemRead.model_validate(item)
    payload.card = _to_master_card_read(card) if card else None
    return payload


@router.get("/cards", response_model=list[MasterCardRead])
async def list_master_cards(
    current_user: AdminUser,
    db: Session = Depends(get_inventory_db),
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[MasterCardRead]:
    """
    List master One Piece cards with optional search.
    """
    query = select(MasterCard)
    if search:
        like = f"%{search}%"
        query = query.where(
            (MasterCard.card_number.ilike(like)) | (MasterCard.name.ilike(like))
        )
    cards = db.exec(query.offset(offset).limit(limit)).all()
    return [_to_master_card_read(card) for card in cards]


@router.post("/cards", response_model=MasterCardRead, status_code=status.HTTP_201_CREATED)
async def create_master_card(
    payload: MasterCardCreate,
    current_user: AdminUser,
    db: Session = Depends(get_inventory_db),
) -> MasterCardRead:
    """
    Create a master card entry.
    """
    existing = db.exec(
        select(MasterCard).where(MasterCard.card_number == payload.card_number)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Card with this number already exists.",
        )
    card = MasterCard(**payload.model_dump())
    db.add(card)
    db.commit()
    db.refresh(card)
    return _to_master_card_read(card)


@router.get("/", response_model=list[InventoryItemRead])
async def list_inventory(
    current_user: AdminUser,
    db: Session = Depends(get_inventory_db),
    status_filter: Optional[InventoryStatus] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[InventoryItemRead]:
    """
    List inventory items with optional status filter.
    """
    query = select(InventoryItem)
    if status_filter:
        query = query.where(InventoryItem.status == status_filter)
    items = db.exec(query.offset(offset).limit(limit)).all()
    card_ids = [item.master_card_id for item in items]
    cards = db.exec(select(MasterCard).where(MasterCard.id.in_(card_ids))).all()
    card_map = {card.id: card for card in cards}
    return [_to_inventory_read(item, card_map.get(item.master_card_id)) for item in items]


@router.post("/", response_model=InventoryItemRead, status_code=status.HTTP_201_CREATED)
async def create_inventory_item(
    payload: InventoryItemCreate,
    current_user: AdminUser,
    db: Session = Depends(get_inventory_db),
) -> InventoryItemRead:
    """
    Add an inventory item for a master card.
    """
    card = db.get(MasterCard, payload.master_card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Master card not found.")
    item = InventoryItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_inventory_read(item, card)


@router.get("/{item_id}", response_model=InventoryItemRead)
async def get_inventory_item(
    item_id: int,
    current_user: AdminUser,
    db: Session = Depends(get_inventory_db),
) -> InventoryItemRead:
    """
    Get a single inventory item.
    """
    item = db.get(InventoryItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found.")
    card = db.get(MasterCard, item.master_card_id)
    return _to_inventory_read(item, card)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inventory_item(
    item_id: int,
    current_user: AdminUser,
    db: Session = Depends(get_inventory_db),
) -> None:
    """
    Delete an inventory item.
    """
    item = db.get(InventoryItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found.")
    db.delete(item)
    db.commit()


@router.get("/stats")
async def inventory_stats(
    current_user: AdminUser,
    db: Session = Depends(get_inventory_db),
) -> dict:
    """
    Get inventory statistics.
    """
    items = db.exec(select(InventoryItem)).all()
    total_items = sum(item.quantity for item in items)
    low_stock_alerts = sum(1 for item in items if item.quantity <= 1)
    return {
        "total_items": total_items,
        "total_value": None,
        "low_stock_alerts": low_stock_alerts,
    }


@router.post("/import/excel", response_model=ImportResult)
async def import_cards_from_excel(
    current_user: AdminUser,
    db: Session = Depends(get_inventory_db),
    file: UploadFile = File(...),
) -> ImportResult:
    """
    Import master cards from Excel export.
    """
    temp_path = Path(f"/tmp/{file.filename}")
    temp_path.write_bytes(await file.read())
    return import_from_excel(db, str(temp_path))
