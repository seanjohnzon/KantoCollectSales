"""
Import service for bringing in card data from external sources.

Supports:
- Excel import from One Piece TCG Tracker (Railway app)
- PriceCharting URL parsing and sync
"""

import re
from datetime import datetime
from typing import Optional, List, Tuple
from pathlib import Path

import pandas as pd
from sqlmodel import Session, select

from app.models.inventory import (
    MasterCard,
    PriceHistory,
    ImportResult,
)


def extract_pricecharting_id(url: str) -> Optional[str]:
    """
    Extract the product slug from a PriceCharting URL.
    
    Args:
        url: PriceCharting URL like 
             https://www.pricecharting.com/game/one-piece-emperors-in-the-new-world/marshalldteach-alternate-art-op09-093
             
    Returns:
        The product slug (e.g., "marshalldteach-alternate-art-op09-093")
    """
    if not url:
        return None
    
    # Extract last part of URL path
    match = re.search(r'pricecharting\.com/game/[^/]+/([^/?]+)', url)
    if match:
        return match.group(1)
    return None


def extract_set_name_from_url(url: str) -> Optional[str]:
    """
    Extract set name from PriceCharting URL.
    
    Args:
        url: PriceCharting URL
        
    Returns:
        Set name like "Emperors in the New World"
    """
    if not url:
        return None
    
    match = re.search(r'pricecharting\.com/game/one-piece-([^/]+)/', url)
    if match:
        # Convert slug to title
        slug = match.group(1)
        # Replace hyphens with spaces and title case
        return slug.replace('-', ' ').title()
    return None


def import_from_excel(
    session: Session,
    file_path: str,
    update_existing: bool = True
) -> ImportResult:
    """
    Import cards from the One Piece TCG Tracker Excel export.
    
    Expected columns:
    - Priority: int
    - Set: str (e.g., "OP-09")
    - Card Name: str
    - Card Number: str (e.g., "OP09-093")
    - Variant: str (e.g., "Alternate Art")
    - Language: str
    - Avg Price ($): float
    - Rarity Score: int
    - Value Score: float
    - Count Bought: int
    - Market URL: str (PriceCharting URL)
    
    Args:
        session: Database session.
        file_path: Path to Excel file.
        update_existing: If True, update existing cards. If False, skip them.
        
    Returns:
        ImportResult with counts and errors.
    """
    errors: List[str] = []
    imported = 0
    skipped = 0
    
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        return ImportResult(
            total_rows=0,
            imported=0,
            skipped=0,
            errors=[f"Failed to read Excel file: {str(e)}"]
        )
    
    total_rows = len(df)
    
    for idx, row in df.iterrows():
        try:
            card_number = str(row.get('Card Number', '')).strip()
            if not card_number:
                errors.append(f"Row {idx + 2}: Missing card number")
                skipped += 1
                continue
            
            # Check if card exists
            existing = session.exec(
                select(MasterCard).where(MasterCard.card_number == card_number)
            ).first()
            
            if existing and not update_existing:
                skipped += 1
                continue
            
            # Parse data
            market_url = str(row.get('Market URL', '')) if pd.notna(row.get('Market URL')) else None
            pricecharting_id = extract_pricecharting_id(market_url) if market_url else None
            set_name = extract_set_name_from_url(market_url) if market_url else None
            
            card_data = {
                'card_number': card_number,
                'name': str(row.get('Card Name', '')).strip(),
                'set_code': str(row.get('Set', '')).strip(),
                'set_name': set_name,
                'variant': str(row.get('Variant', '')).strip() if pd.notna(row.get('Variant')) else None,
                'pricecharting_url': market_url,
                'pricecharting_id': pricecharting_id,
                'rarity_score': int(row.get('Rarity Score', 0)) if pd.notna(row.get('Rarity Score')) else None,
                'manual_priority': int(row.get('Priority', 0)) if pd.notna(row.get('Priority')) else None,
                'updated_at': datetime.utcnow(),
            }
            
            if existing:
                # Update existing
                for key, value in card_data.items():
                    setattr(existing, key, value)
                session.add(existing)
                card = existing
            else:
                # Create new
                card = MasterCard(**card_data)
                session.add(card)
            
            session.flush()  # Get the ID
            
            # Add price history if we have a price
            avg_price = row.get('Avg Price ($)')
            if pd.notna(avg_price) and float(avg_price) > 0:
                price_record = PriceHistory(
                    master_card_id=card.id,
                    price_usd=float(avg_price),
                    source="excel_import",
                    recorded_at=datetime.utcnow()
                )
                session.add(price_record)
            
            imported += 1
            
        except Exception as e:
            errors.append(f"Row {idx + 2}: {str(e)}")
            skipped += 1
    
    session.commit()
    
    return ImportResult(
        total_rows=total_rows,
        imported=imported,
        skipped=skipped,
        errors=errors
    )


def sync_price_from_pricecharting(
    session: Session,
    card: MasterCard,
    price_data: dict
) -> Optional[PriceHistory]:
    """
    Add a new price record from PriceCharting API response.
    
    Args:
        session: Database session.
        card: The MasterCard to update.
        price_data: Dict with 'loose_price', 'cib_price', 'new_price'.
        
    Returns:
        The created PriceHistory record.
    """
    # Get main price (loose is most common for cards)
    price_usd = price_data.get('loose_price') or price_data.get('cib_price') or price_data.get('new_price')
    
    if not price_usd:
        return None
    
    record = PriceHistory(
        master_card_id=card.id,
        price_usd=price_usd,
        loose_price=price_data.get('loose_price'),
        cib_price=price_data.get('cib_price'),
        new_price=price_data.get('new_price'),
        source="pricecharting",
        recorded_at=datetime.utcnow()
    )
    
    session.add(record)
    session.commit()
    
    return record


def get_latest_price(session: Session, card_id: int) -> Optional[float]:
    """
    Get the most recent price for a card.
    
    Args:
        session: Database session.
        card_id: MasterCard ID.
        
    Returns:
        Latest price or None.
    """
    result = session.exec(
        select(PriceHistory)
        .where(PriceHistory.master_card_id == card_id)
        .order_by(PriceHistory.recorded_at.desc())
    ).first()
    
    return result.price_usd if result else None


def get_price_trend(
    session: Session,
    card_id: int,
    days: int = 30
) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    """
    Calculate price trend for a card.
    
    Args:
        session: Database session.
        card_id: MasterCard ID.
        days: Number of days to look back.
        
    Returns:
        Tuple of (current_price, change_percent, trend_direction)
    """
    from datetime import timedelta
    
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    prices = session.exec(
        select(PriceHistory)
        .where(PriceHistory.master_card_id == card_id)
        .where(PriceHistory.recorded_at >= cutoff)
        .order_by(PriceHistory.recorded_at.asc())
    ).all()
    
    if len(prices) < 2:
        current = prices[-1].price_usd if prices else None
        return (current, None, "stable")
    
    first_price = prices[0].price_usd
    current_price = prices[-1].price_usd
    
    if first_price == 0:
        return (current_price, None, "stable")
    
    change_pct = ((current_price - first_price) / first_price) * 100
    
    if change_pct > 5:
        trend = "up"
    elif change_pct < -5:
        trend = "down"
    else:
        trend = "stable"
    
    return (current_price, round(change_pct, 2), trend)
