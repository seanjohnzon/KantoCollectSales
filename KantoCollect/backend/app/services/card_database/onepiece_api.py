"""
One Piece Card Game API wrapper.

Uses onepiece-cardgame.dev API to fetch card data.
Caches results locally in SQLite to avoid repeated API calls.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import httpx
from sqlmodel import Session, select

from ...models.card import CardCache, CardGame, CardSource

logger = logging.getLogger(__name__)


class OnePieceCardAPI:
    """
    API wrapper for One Piece card database.
    
    Primary source: onepiece-cardgame.dev
    Caches all card data locally for fast matching.
    """
    
    # API endpoints
    BASE_URL = "https://onepiece-cardgame.dev/api"
    
    # Alternative: enkidex (another One Piece TCG database)
    ENKIDEX_URL = "https://apiv2.enkideks.fr/api/v2"
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self._client = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def fetch_all_cards(self, force_refresh: bool = False) -> int:
        """
        Fetch all One Piece cards and cache them locally.
        
        Args:
            force_refresh: If True, refresh even if cache is recent.
            
        Returns:
            Number of cards cached.
        """
        # Check if we have recent cache
        if not force_refresh:
            recent_card = self.db.exec(
                select(CardCache)
                .where(CardCache.game == CardGame.ONE_PIECE)
                .where(CardCache.updated_at > datetime.utcnow() - timedelta(days=7))
            ).first()
            
            if recent_card:
                count = self.db.exec(
                    select(CardCache)
                    .where(CardCache.game == CardGame.ONE_PIECE)
                ).all()
                logger.info(f"Using cached One Piece cards ({len(count)} cards)")
                return len(count)
        
        # Try primary API first
        cards = await self._fetch_from_primary()
        
        # Fall back to enkidex if primary fails
        if not cards:
            logger.warning("Primary API failed, trying Enkidex...")
            cards = await self._fetch_from_enkidex()
        
        if not cards:
            logger.error("All card APIs failed!")
            return 0
        
        # Cache the cards
        cached_count = await self._cache_cards(cards)
        logger.info(f"Cached {cached_count} One Piece cards")
        
        return cached_count
    
    async def _fetch_from_primary(self) -> List[Dict[str, Any]]:
        """
        Fetch cards from onepiece-cardgame.dev.
        
        The API structure is typically:
        GET /api/cards - returns all cards
        """
        try:
            client = await self._get_client()
            
            # Try different known endpoints
            endpoints = [
                f"{self.BASE_URL}/cards",
                f"{self.BASE_URL}/card",
                "https://onepiece-cardgame.dev/cards.json",
            ]
            
            for endpoint in endpoints:
                try:
                    response = await client.get(endpoint, follow_redirects=True)
                    if response.status_code == 200:
                        data = response.json()
                        # Handle different response structures
                        if isinstance(data, list):
                            return data
                        elif isinstance(data, dict):
                            if "cards" in data:
                                return data["cards"]
                            elif "data" in data:
                                return data["data"]
                        logger.info(f"Successfully fetched from {endpoint}")
                except Exception as e:
                    logger.debug(f"Endpoint {endpoint} failed: {e}")
                    continue
            
            return []
            
        except Exception as e:
            logger.error(f"Primary API fetch failed: {e}")
            return []
    
    async def _fetch_from_enkidex(self) -> List[Dict[str, Any]]:
        """
        Fetch cards from Enkidex API (alternative source).
        
        API: https://apiv2.enkideks.fr/api/v2/cards
        """
        try:
            client = await self._get_client()
            
            all_cards = []
            page = 1
            
            while True:
                response = await client.get(
                    f"{self.ENKIDEX_URL}/cards",
                    params={"page": page, "per_page": 100}
                )
                
                if response.status_code != 200:
                    break
                    
                data = response.json()
                cards = data.get("data", [])
                
                if not cards:
                    break
                    
                all_cards.extend(cards)
                
                # Check pagination
                if data.get("current_page", 0) >= data.get("last_page", 0):
                    break
                    
                page += 1
                await asyncio.sleep(0.1)  # Rate limiting
            
            return all_cards
            
        except Exception as e:
            logger.error(f"Enkidex API fetch failed: {e}")
            return []
    
    async def _cache_cards(self, cards: List[Dict[str, Any]]) -> int:
        """
        Cache cards in local database.
        
        Handles different API response formats.
        """
        cached = 0
        
        for card_data in cards:
            try:
                # Normalize card data from different API formats
                card = self._normalize_card_data(card_data)
                
                if not card:
                    continue
                
                # Check if already exists
                existing = self.db.exec(
                    select(CardCache)
                    .where(CardCache.external_id == card["external_id"])
                    .where(CardCache.game == CardGame.ONE_PIECE)
                ).first()
                
                if existing:
                    # Update existing
                    for key, value in card.items():
                        if key != "external_id" and value is not None:
                            setattr(existing, key, value)
                    existing.updated_at = datetime.utcnow()
                else:
                    # Create new
                    new_card = CardCache(
                        game=CardGame.ONE_PIECE,
                        source=CardSource.ONEPIECE_CARDGAME_DEV,
                        **card
                    )
                    self.db.add(new_card)
                
                cached += 1
                
            except Exception as e:
                logger.debug(f"Failed to cache card: {e}")
                continue
        
        self.db.commit()
        return cached
    
    def _normalize_card_data(self, raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Normalize card data from different API formats.
        
        Different APIs use different field names:
        - onepiece-cardgame.dev: name, card_id, cost, power, color, etc.
        - enkidex: name, code, cost, power, colors, etc.
        """
        try:
            # Get external ID (required)
            external_id = (
                raw.get("id") or 
                raw.get("card_id") or 
                raw.get("code") or 
                raw.get("cardId")
            )
            
            if not external_id:
                return None
            
            # Get name (required)
            name = raw.get("name") or raw.get("cardName")
            if not name:
                return None
            
            # Normalize colors
            color = raw.get("color") or raw.get("colors")
            if isinstance(color, list):
                color = "/".join(color)
            
            # Get card number
            card_number = (
                raw.get("card_number") or
                raw.get("cardNumber") or
                raw.get("code") or
                raw.get("id")
            )
            
            # Get set name
            set_name = (
                raw.get("set") or
                raw.get("setName") or
                raw.get("expansion") or
                raw.get("series")
            )
            if isinstance(set_name, dict):
                set_name = set_name.get("name", str(set_name))
            
            # Get image URL
            image_url = (
                raw.get("image") or
                raw.get("imageUrl") or
                raw.get("image_url") or
                raw.get("img")
            )
            if isinstance(image_url, dict):
                image_url = image_url.get("url") or image_url.get("large")
            
            # Parse cost and power
            cost = raw.get("cost") or raw.get("life")
            if cost is not None:
                try:
                    cost = int(cost)
                except (ValueError, TypeError):
                    cost = None
            
            power = raw.get("power") or raw.get("attack")
            if power is not None:
                try:
                    # Handle "6000" or 6000
                    power = int(str(power).replace("+", "").replace("-", ""))
                except (ValueError, TypeError):
                    power = None
            
            return {
                "external_id": str(external_id),
                "name": name,
                "set_name": set_name,
                "card_number": card_number,
                "cost": cost,
                "power": power,
                "color": color,
                "rarity": raw.get("rarity"),
                "card_type": raw.get("type") or raw.get("cardType") or raw.get("category"),
                "image_url": image_url,
            }
            
        except Exception as e:
            logger.debug(f"Failed to normalize card: {e}")
            return None
    
    def search_by_attributes(
        self,
        name: Optional[str] = None,
        cost: Optional[int] = None,
        power: Optional[int] = None,
        color: Optional[str] = None,
        card_type: Optional[str] = None,
        limit: int = 10
    ) -> List[CardCache]:
        """
        Search cached cards by attributes.
        
        This is the main method for finding matching cards based on
        what the AI extracts from an image.
        
        Args:
            name: Card name (fuzzy match)
            cost: Card cost (exact match)
            power: Card power (exact match)
            color: Card color (partial match)
            card_type: Card type (exact match)
            limit: Max results
            
        Returns:
            List of matching CardCache objects.
        """
        query = select(CardCache).where(CardCache.game == CardGame.ONE_PIECE)
        
        # Apply filters
        if name:
            # Fuzzy name search - check if name contains the search term
            query = query.where(CardCache.name.ilike(f"%{name}%"))
        
        if cost is not None:
            query = query.where(CardCache.cost == cost)
        
        if power is not None:
            # Allow some tolerance for power (±500)
            query = query.where(
                CardCache.power.between(power - 500, power + 500)
            )
        
        if color:
            query = query.where(CardCache.color.ilike(f"%{color}%"))
        
        if card_type:
            query = query.where(CardCache.card_type.ilike(f"%{card_type}%"))
        
        query = query.limit(limit)
        
        return list(self.db.exec(query).all())
    
    def get_by_card_number(self, card_number: str) -> Optional[CardCache]:
        """
        Get card by exact card number (e.g., "OP01-001").
        
        This is the most accurate way to identify a card.
        """
        return self.db.exec(
            select(CardCache)
            .where(CardCache.game == CardGame.ONE_PIECE)
            .where(CardCache.card_number == card_number)
        ).first()
    
    def get_all_cards(self) -> List[CardCache]:
        """Get all cached One Piece cards."""
        return list(self.db.exec(
            select(CardCache).where(CardCache.game == CardGame.ONE_PIECE)
        ).all())
    
    def get_card_count(self) -> int:
        """Get count of cached One Piece cards."""
        return len(self.get_all_cards())
