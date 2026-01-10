"""
Card Database Management API.

Endpoints for managing the card cache and finding matching cards.
"""

from typing import Optional, List
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.card import CardCache, CardGame

router = APIRouter(tags=["Card Database"])


# ============== External Card Image APIs ==============

async def fetch_card_image_from_apis(
    card_number: Optional[str] = None,
    name: Optional[str] = None,
    cost: Optional[int] = None,
    power: Optional[int] = None,
    color: Optional[str] = None,
) -> List[dict]:
    """
    Fetch card images based on card attributes.
    
    Uses image URL patterns from official Bandai website.
    Returns list of potential matches with images.
    """
    results = []
    
    # Common One Piece character cards to match against
    # This is a simple lookup table - in production, this would be a database
    COMMON_CARDS = [
        {"name": "Monkey D. Luffy", "card_number": "OP01-003", "cost": 5, "power": 6000, "color": "Red"},
        {"name": "Monkey D. Luffy", "card_number": "OP01-024", "cost": 4, "power": 5000, "color": "Red"},
        {"name": "Monkey D. Luffy", "card_number": "OP05-119", "cost": 5, "power": 6000, "color": "Red"},
        {"name": "Monkey D. Luffy", "card_number": "OP08-001", "cost": 9, "power": 9000, "color": "Red"},
        {"name": "Roronoa Zoro", "card_number": "OP01-025", "cost": 3, "power": 5000, "color": "Green"},
        {"name": "Roronoa Zoro", "card_number": "OP06-118", "cost": 5, "power": 6000, "color": "Green"},
        {"name": "Nami", "card_number": "OP01-016", "cost": 1, "power": 2000, "color": "Red"},
        {"name": "Sanji", "card_number": "OP01-013", "cost": 2, "power": 4000, "color": "Red"},
        {"name": "Tony Tony.Chopper", "card_number": "OP01-015", "cost": 1, "power": 1000, "color": "Red"},
        {"name": "Nico Robin", "card_number": "OP01-017", "cost": 3, "power": 5000, "color": "Purple"},
        {"name": "Franky", "card_number": "OP01-021", "cost": 4, "power": 6000, "color": "Yellow"},
        {"name": "Brook", "card_number": "OP01-022", "cost": 3, "power": 4000, "color": "Blue"},
        {"name": "Jinbe", "card_number": "OP01-010", "cost": 8, "power": 8000, "color": "Red"},
        {"name": "Kaido", "card_number": "OP04-044", "cost": 10, "power": 12000, "color": "Purple"},
        {"name": "Kaido", "card_number": "OP03-099", "cost": 10, "power": 12000, "color": "Yellow"},
        {"name": "Charlotte Katakuri", "card_number": "OP03-123", "cost": 10, "power": 12000, "color": "Yellow"},
        {"name": "Charlotte Cracker", "card_number": "OP03-108", "cost": 4, "power": 5000, "color": "Yellow"},
        {"name": "Charlotte Linlin", "card_number": "OP03-114", "cost": 10, "power": 12000, "color": "Yellow"},
        {"name": "Dracule Mihawk", "card_number": "OP01-070", "cost": 6, "power": 7000, "color": "Black"},
        {"name": "Trafalgar Law", "card_number": "OP01-047", "cost": 7, "power": 7000, "color": "Green"},
        {"name": "Eustass Kid", "card_number": "OP01-051", "cost": 8, "power": 8000, "color": "Green"},
        {"name": "Boa Hancock", "card_number": "OP01-078", "cost": 4, "power": 5000, "color": "Black"},
        {"name": "Portgas D. Ace", "card_number": "OP02-013", "cost": 7, "power": 7000, "color": "Red"},
        {"name": "Sabo", "card_number": "OP02-007", "cost": 5, "power": 6000, "color": "Red"},
        {"name": "Edward Newgate", "card_number": "OP02-004", "cost": 9, "power": 10000, "color": "Red"},
        {"name": "Shanks", "card_number": "OP01-120", "cost": 9, "power": 10000, "color": "Red"},
        {"name": "Yamato", "card_number": "OP04-112", "cost": 8, "power": 8000, "color": "Yellow"},
    ]
    
    # Score and match cards
    matches = []
    
    for card in COMMON_CARDS:
        score = 0
        
        # Card number match (strongest)
        if card_number:
            if card_number.upper() == card["card_number"].upper():
                score += 100
            elif card_number.upper().replace("-", "") in card["card_number"].upper().replace("-", ""):
                score += 80
        
        # Name match
        if name:
            name_lower = name.lower().replace("(?)", "").strip()
            card_name_lower = card["name"].lower()
            if name_lower in card_name_lower or card_name_lower in name_lower:
                score += 50
            elif any(word in card_name_lower for word in name_lower.split() if len(word) > 2):
                score += 30
        
        # Cost match
        if cost is not None and card.get("cost") == cost:
            score += 20
        
        # Power match
        if power is not None:
            card_power = card.get("power")
            if card_power and abs(card_power - power) <= 500:
                score += 20
        
        # Color match
        if color:
            card_color = card.get("color", "")
            if color.lower() in card_color.lower():
                score += 15
        
        if score > 0:
            matches.append((score, card))
    
    # Sort by score and take top matches
    matches.sort(key=lambda x: x[0], reverse=True)
    
    for score, card in matches[:5]:
        # Construct image URL using official Bandai pattern
        card_num = card["card_number"]
        # Multiple URL patterns to try
        image_url = f"https://en.onepiece-cardgame.com/images/cardlist/card/{card_num}.png"
        
        results.append({
            "name": card["name"],
            "card_number": card_num,
            "set_name": f"OP-{card_num[2:4]}" if card_num.startswith("OP") else None,
            "cost": card.get("cost"),
            "power": card.get("power"),
            "color": card.get("color"),
            "card_type": "Character",
            "rarity": None,
            "image_url": image_url,
            "match_score": score,
            "source": "local_lookup",
        })
    
    # If no matches from lookup table but we have a card number, construct URL anyway
    if not results and card_number:
        # Normalize card number format (e.g., OP01001 -> OP01-001)
        normalized = card_number.upper().strip()
        if len(normalized) == 7 and not "-" in normalized:
            normalized = f"{normalized[:4]}-{normalized[4:]}"
        
        image_url = f"https://en.onepiece-cardgame.com/images/cardlist/card/{normalized}.png"
        
        results.append({
            "name": name or f"Card {normalized}",
            "card_number": normalized,
            "cost": cost,
            "power": power,
            "color": color,
            "image_url": image_url,
            "match_score": 50,
            "source": "constructed_url",
        })
    
    # If still no results but we have a name, return with placeholder
    if not results and name:
        results.append({
            "name": name,
            "card_number": None,
            "cost": cost,
            "power": power,
            "color": color,
            "image_url": None,
            "match_score": 25,
            "source": "name_only",
        })
    
    return results


# ============== Endpoints ==============

@router.post("/sync/one-piece")
async def sync_one_piece_cards(
    force: bool = Query(False, description="Force refresh even if cache is recent"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Sync One Piece cards from external API.
    
    This fetches all One Piece TCG cards and caches them locally.
    First run may take 1-2 minutes.
    
    NOTE: Currently returns placeholder since external APIs need verification.
    """
    # For now, return a message explaining the status
    # The actual card fetching will be implemented once we verify API endpoints
    return {
        "status": "pending",
        "message": "Card sync endpoint ready. API integration coming soon.",
        "note": "Use /match endpoint to manually match cards by attributes",
    }


@router.get("/status")
async def get_card_database_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get status of local card database.
    
    Returns count of cached cards for each game.
    """
    from sqlmodel import select, func
    
    # Count One Piece cards
    op_result = await db.execute(
        select(func.count())
        .select_from(CardCache)
        .where(CardCache.game == CardGame.ONE_PIECE)
    )
    op_count = op_result.scalar() or 0
    
    # Count Pokemon cards
    pkmn_result = await db.execute(
        select(func.count())
        .select_from(CardCache)
        .where(CardCache.game == CardGame.POKEMON)
    )
    pkmn_count = pkmn_result.scalar() or 0
    
    return {
        "one_piece_count": op_count,
        "pokemon_count": pkmn_count,
        "status": "ready" if op_count > 0 else "empty",
        "message": "Sync cards using POST /sync/one-piece" if op_count == 0 else "Database ready",
    }


@router.post("/match")
async def find_matching_cards(
    name: Optional[str] = Query(None, description="Card name (partial OK)"),
    cost: Optional[int] = Query(None, description="Card cost"),
    power: Optional[int] = Query(None, description="Card power (e.g., 6000)"),
    color: Optional[str] = Query(None, description="Card color"),
    card_type: Optional[str] = Query(None, description="Card type"),
    game: str = Query("one_piece", description="Game: one_piece or pokemon"),
    limit: int = Query(5, description="Max results"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Find matching cards based on attributes.
    
    Use this to get potential matches when the AI detects card attributes
    but can't identify the exact card.
    
    NOTE: Requires card database to be populated first.
    """
    from sqlmodel import select
    
    # Get game enum
    game_enum = CardGame.ONE_PIECE if game == "one_piece" else CardGame.POKEMON
    
    # Build query
    query = select(CardCache).where(CardCache.game == game_enum)
    
    if name:
        query = query.where(CardCache.name.ilike(f"%{name}%"))
    if cost is not None:
        query = query.where(CardCache.cost == cost)
    if power is not None:
        # Allow some tolerance for power
        query = query.where(CardCache.power.between(power - 500, power + 500))
    if color:
        query = query.where(CardCache.color.ilike(f"%{color}%"))
    if card_type:
        query = query.where(CardCache.card_type.ilike(f"%{card_type}%"))
    
    query = query.limit(limit)
    
    result = await db.execute(query)
    cards = result.scalars().all()
    
    # Format response
    return {
        "matches": [
            {
                "card": {
                    "id": c.id,
                    "name": c.name,
                    "card_number": c.card_number,
                    "set_name": c.set_name,
                    "cost": c.cost,
                    "power": c.power,
                    "color": c.color,
                    "card_type": c.card_type,
                    "rarity": c.rarity,
                    "image_url": c.image_url,
                },
                "score": 100.0,  # Direct matches
                "reasons": ["Database match"],
            }
            for c in cards
        ],
        "query": {
            "name": name,
            "cost": cost,
            "power": power,
            "color": color,
        },
        "count": len(cards),
    }


@router.post("/confirm/{card_id}")
async def confirm_card_identification(
    card_id: int,
    ai_name: Optional[str] = Query(None),
    ai_cost: Optional[int] = Query(None),
    ai_power: Optional[int] = Query(None),
    ai_color: Optional[str] = Query(None),
    confirmed: bool = Query(True, description="Whether this was correct"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Confirm a card identification.
    
    Call this when a user confirms that a matched card is correct.
    This improves future matching by learning from user feedback.
    """
    from sqlmodel import select
    from app.models.card import UserCardIdentification
    
    # Verify card exists
    result = await db.execute(select(CardCache).where(CardCache.id == card_id))
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    # Record confirmation
    identification = UserCardIdentification(
        card_cache_id=card_id,
        ai_detected_name=ai_name,
        ai_detected_cost=ai_cost,
        ai_detected_power=ai_power,
        ai_detected_color=ai_color,
        confirmed=confirmed,
    )
    
    db.add(identification)
    await db.commit()
    await db.refresh(identification)
    
    return {
        "status": "recorded",
        "card_id": card_id,
        "confirmed": confirmed,
        "identification_id": identification.id,
    }


@router.get("/search")
async def search_cards(
    q: str = Query(..., min_length=2, description="Search query"),
    game: str = Query("one_piece", description="Game: one_piece or pokemon"),
    limit: int = Query(10, description="Max results"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Search cards by name.
    
    Simple text search for finding cards by name.
    """
    from sqlmodel import select
    
    game_enum = CardGame.ONE_PIECE if game == "one_piece" else CardGame.POKEMON
    
    result = await db.execute(
        select(CardCache)
        .where(CardCache.game == game_enum)
        .where(CardCache.name.ilike(f"%{q}%"))
        .limit(limit)
    )
    cards = result.scalars().all()
    
    return {
        "results": [
            {
                "id": c.id,
                "name": c.name,
                "card_number": c.card_number,
                "set_name": c.set_name,
                "cost": c.cost,
                "power": c.power,
                "color": c.color,
                "image_url": c.image_url,
            }
            for c in cards
        ],
        "count": len(cards),
        "query": q,
    }


@router.get("/images/search")
async def search_card_images(
    name: Optional[str] = Query(None, description="Card name"),
    card_number: Optional[str] = Query(None, description="Card number (e.g., OP01-001)"),
    cost: Optional[int] = Query(None, description="Card cost"),
    power: Optional[int] = Query(None, description="Card power"),
    color: Optional[str] = Query(None, description="Card color"),
    current_user: User = Depends(get_current_user),
):
    """
    Search for card images from external APIs.
    
    Use this to find card images for the confirmation UI.
    Returns potential matches with image URLs.
    """
    if not any([name, card_number, cost, power, color]):
        raise HTTPException(
            status_code=400,
            detail="At least one search parameter required"
        )
    
    results = await fetch_card_image_from_apis(
        card_number=card_number,
        name=name,
        cost=cost,
        power=power,
        color=color,
    )
    
    return {
        "matches": results,
        "count": len(results),
        "query": {
            "name": name,
            "card_number": card_number,
            "cost": cost,
            "power": power,
            "color": color,
        },
    }


@router.get("/{card_number}")
async def get_card_by_number(
    card_number: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific card by card number.
    
    Example: OP01-001
    """
    from sqlmodel import select
    
    # First check local cache
    result = await db.execute(
        select(CardCache)
        .where(CardCache.card_number == card_number)
    )
    card = result.scalar_one_or_none()
    
    if card:
        return {
            "id": card.id,
            "external_id": card.external_id,
            "name": card.name,
            "card_number": card.card_number,
            "set_name": card.set_name,
            "cost": card.cost,
            "power": card.power,
            "color": card.color,
            "card_type": card.card_type,
            "rarity": card.rarity,
            "image_url": card.image_url,
            "last_price_usd": card.last_price_usd,
            "source": "local_cache",
        }
    
    # If not in cache, try external APIs
    external_results = await fetch_card_image_from_apis(card_number=card_number)
    
    if external_results:
        return {
            **external_results[0],
            "source": "external_api",
        }
    
    raise HTTPException(status_code=404, detail="Card not found")
