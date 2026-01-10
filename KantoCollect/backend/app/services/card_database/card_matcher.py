"""
Card Matcher Service - matches AI-detected attributes to actual cards.

Uses a scoring system to find the best matching cards from the database,
then presents options to the user for confirmation.
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher
from sqlmodel import Session, select

from ...models.card import CardCache, CardGame, UserCardIdentification

logger = logging.getLogger(__name__)


@dataclass
class MatchCandidate:
    """A potential card match with scoring details."""
    card: CardCache
    total_score: float  # 0.0 to 1.0
    name_score: float
    attribute_score: float
    match_reasons: List[str]


@dataclass  
class AIDetectedAttributes:
    """Attributes extracted by AI from card image."""
    name: Optional[str] = None
    cost: Optional[int] = None
    power: Optional[int] = None
    color: Optional[str] = None
    card_type: Optional[str] = None
    rarity: Optional[str] = None
    set_code: Optional[str] = None  # e.g., "OP01"
    visible_text: Optional[str] = None  # Any other visible text


class CardMatcher:
    """
    Matches AI-detected card attributes to actual cards in the database.
    
    Scoring system:
    - Name similarity: 40% weight
    - Cost match: 15% weight
    - Power match: 15% weight
    - Color match: 15% weight
    - Type match: 10% weight
    - Previous user confirmations: 5% bonus
    """
    
    WEIGHT_NAME = 0.40
    WEIGHT_COST = 0.15
    WEIGHT_POWER = 0.15
    WEIGHT_COLOR = 0.15
    WEIGHT_TYPE = 0.10
    BONUS_USER_CONFIRMED = 0.05
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def find_matches(
        self,
        detected: AIDetectedAttributes,
        game: CardGame = CardGame.ONE_PIECE,
        max_results: int = 5
    ) -> List[MatchCandidate]:
        """
        Find best matching cards for AI-detected attributes.
        
        Args:
            detected: Attributes extracted by AI.
            game: Which card game to search.
            max_results: Maximum candidates to return.
            
        Returns:
            List of MatchCandidates sorted by score (highest first).
        """
        # If we have a card number, try exact match first
        if detected.set_code and detected.name:
            # Try to construct potential card numbers
            exact = self._try_exact_match(detected, game)
            if exact and exact.card_number:
                return [MatchCandidate(
                    card=exact,
                    total_score=1.0,
                    name_score=1.0,
                    attribute_score=1.0,
                    match_reasons=["Exact card number match"]
                )]
        
        # Get all cards for the game
        all_cards = self._get_all_cards(game)
        
        if not all_cards:
            logger.warning(f"No cards cached for {game}")
            return []
        
        # Score each card
        candidates = []
        for card in all_cards:
            score, reasons = self._score_match(card, detected)
            if score > 0.1:  # Minimum threshold
                candidates.append(MatchCandidate(
                    card=card,
                    total_score=score,
                    name_score=self._name_similarity(
                        detected.name or "", card.name
                    ),
                    attribute_score=self._attribute_score(card, detected),
                    match_reasons=reasons
                ))
        
        # Sort by score
        candidates.sort(key=lambda x: x.total_score, reverse=True)
        
        # Check for previous user confirmations
        candidates = self._boost_user_confirmed(candidates, detected)
        
        return candidates[:max_results]
    
    def _try_exact_match(
        self, 
        detected: AIDetectedAttributes, 
        game: CardGame
    ) -> Optional[CardCache]:
        """Try to find an exact match by card number."""
        if not detected.set_code:
            return None
        
        # Try different card number formats
        potential_numbers = []
        if detected.name:
            # OP01-001 format - would need to know the number
            # For now, just search by set code prefix
            pass
        
        # Search by set prefix
        cards = self.db.exec(
            select(CardCache)
            .where(CardCache.game == game)
            .where(CardCache.card_number.ilike(f"{detected.set_code}%"))
            .where(CardCache.name.ilike(f"%{detected.name}%") if detected.name else True)
        ).all()
        
        if len(cards) == 1:
            return cards[0]
        
        return None
    
    def _get_all_cards(self, game: CardGame) -> List[CardCache]:
        """Get all cached cards for a game."""
        return list(self.db.exec(
            select(CardCache).where(CardCache.game == game)
        ).all())
    
    def _score_match(
        self, 
        card: CardCache, 
        detected: AIDetectedAttributes
    ) -> Tuple[float, List[str]]:
        """
        Calculate match score between card and detected attributes.
        
        Returns:
            (total_score, list of match reasons)
        """
        score = 0.0
        reasons = []
        
        # Name similarity
        if detected.name:
            name_sim = self._name_similarity(detected.name, card.name)
            score += name_sim * self.WEIGHT_NAME
            if name_sim > 0.8:
                reasons.append(f"Name match: {name_sim:.0%}")
            elif name_sim > 0.5:
                reasons.append(f"Partial name: {name_sim:.0%}")
        
        # Cost match
        if detected.cost is not None and card.cost is not None:
            if detected.cost == card.cost:
                score += self.WEIGHT_COST
                reasons.append(f"Cost match: {card.cost}")
        
        # Power match
        if detected.power is not None and card.power is not None:
            power_diff = abs(detected.power - card.power)
            if power_diff == 0:
                score += self.WEIGHT_POWER
                reasons.append(f"Power exact: {card.power}")
            elif power_diff <= 1000:  # Close match
                score += self.WEIGHT_POWER * 0.5
                reasons.append(f"Power close: {card.power}")
        
        # Color match
        if detected.color and card.color:
            if self._color_matches(detected.color, card.color):
                score += self.WEIGHT_COLOR
                reasons.append(f"Color: {card.color}")
        
        # Type match
        if detected.card_type and card.card_type:
            if detected.card_type.lower() in card.card_type.lower():
                score += self.WEIGHT_TYPE
                reasons.append(f"Type: {card.card_type}")
        
        return score, reasons
    
    def _name_similarity(self, name1: str, name2: str) -> float:
        """
        Calculate name similarity using multiple methods.
        
        Handles cases like:
        - "Luffy" matching "Monkey D. Luffy"
        - "Zoro" matching "Roronoa Zoro"
        """
        if not name1 or not name2:
            return 0.0
        
        n1 = name1.lower().strip()
        n2 = name2.lower().strip()
        
        # Exact match
        if n1 == n2:
            return 1.0
        
        # One contains the other
        if n1 in n2 or n2 in n1:
            return 0.85
        
        # Sequence matcher for fuzzy matching
        return SequenceMatcher(None, n1, n2).ratio()
    
    def _color_matches(self, detected: str, actual: str) -> bool:
        """Check if detected color matches card color."""
        if not detected or not actual:
            return False
        
        # Normalize
        d_colors = set(detected.lower().replace("/", ",").split(","))
        a_colors = set(actual.lower().replace("/", ",").split(","))
        
        d_colors = {c.strip() for c in d_colors if c.strip()}
        a_colors = {c.strip() for c in a_colors if c.strip()}
        
        # Any overlap counts as match
        return bool(d_colors & a_colors)
    
    def _attribute_score(
        self, 
        card: CardCache, 
        detected: AIDetectedAttributes
    ) -> float:
        """Calculate just the attribute portion of the score."""
        score = 0.0
        max_score = 0.0
        
        if detected.cost is not None:
            max_score += 1
            if card.cost == detected.cost:
                score += 1
        
        if detected.power is not None:
            max_score += 1
            if card.power and abs(card.power - detected.power) <= 1000:
                score += 1
        
        if detected.color:
            max_score += 1
            if self._color_matches(detected.color, card.color or ""):
                score += 1
        
        if max_score == 0:
            return 0.0
        
        return score / max_score
    
    def _boost_user_confirmed(
        self,
        candidates: List[MatchCandidate],
        detected: AIDetectedAttributes
    ) -> List[MatchCandidate]:
        """
        Boost scores for cards that users have previously confirmed
        for similar detections.
        """
        if not detected.name:
            return candidates
        
        # Find previous confirmations for similar AI detections
        confirmations = self.db.exec(
            select(UserCardIdentification)
            .where(UserCardIdentification.confirmed == True)
            .where(
                UserCardIdentification.ai_detected_name.ilike(f"%{detected.name}%")
            )
        ).all()
        
        confirmed_card_ids = {c.card_cache_id for c in confirmations}
        
        # Boost candidates that have been confirmed before
        for candidate in candidates:
            if candidate.card.id in confirmed_card_ids:
                candidate.total_score = min(1.0, candidate.total_score + self.BONUS_USER_CONFIRMED)
                candidate.match_reasons.append("Previously confirmed")
        
        # Re-sort after boosting
        candidates.sort(key=lambda x: x.total_score, reverse=True)
        
        return candidates
    
    def record_confirmation(
        self,
        card_id: int,
        detected: AIDetectedAttributes,
        confirmed: bool = True
    ) -> UserCardIdentification:
        """
        Record a user's confirmation of a card match.
        
        This improves future matching by learning from user feedback.
        """
        identification = UserCardIdentification(
            card_cache_id=card_id,
            ai_detected_name=detected.name,
            ai_detected_cost=detected.cost,
            ai_detected_power=detected.power,
            ai_detected_color=detected.color,
            confirmed=confirmed
        )
        
        self.db.add(identification)
        self.db.commit()
        self.db.refresh(identification)
        
        logger.info(f"Recorded {'confirmation' if confirmed else 'rejection'} for card {card_id}")
        
        return identification


def create_detected_attributes(ai_output: Dict[str, Any]) -> AIDetectedAttributes:
    """
    Helper to create AIDetectedAttributes from AI output.
    
    Handles various output formats from Claude.
    """
    return AIDetectedAttributes(
        name=ai_output.get("name") or ai_output.get("card_name"),
        cost=_safe_int(ai_output.get("cost")),
        power=_safe_int(ai_output.get("power")),
        color=ai_output.get("color"),
        card_type=ai_output.get("type") or ai_output.get("card_type"),
        rarity=ai_output.get("rarity"),
        set_code=ai_output.get("set") or ai_output.get("set_code"),
        visible_text=ai_output.get("visible_text")
    )


def _safe_int(value: Any) -> Optional[int]:
    """Safely convert value to int."""
    if value is None:
        return None
    try:
        # Handle strings like "6000" or "5"
        return int(str(value).replace("+", "").replace("-", "").strip())
    except (ValueError, TypeError):
        return None
