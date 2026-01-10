"""
Deal Analyzer main service.

Orchestrates AI card detection and price lookup for lot valuation.

COST NOTES:
- Using Claude 3 Haiku for card detection (~$0.25/M input, $1.25/M output)
- Average image analysis: ~1500 input tokens, ~500 output tokens
- Estimated cost per analysis: ~$0.001 (0.1 cents)
- To keep sustainable: ~1000 analyses per $1
"""

import base64
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import anthropic

from app.core.config import settings
from app.services.price_lookup.pricecharting import (
    PriceChartingService,
    LotItem,
    ProductCategory,
)

# Simple usage tracking
logger = logging.getLogger(__name__)

class UsageTracker:
    """Track API usage for cost monitoring."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.total_calls = 0
            cls._instance.total_input_tokens = 0
            cls._instance.total_output_tokens = 0
            cls._instance.session_start = datetime.utcnow()
        return cls._instance
    
    def log_call(self, input_tokens: int, output_tokens: int):
        """Log an API call."""
        self.total_calls += 1
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        
        # Estimate cost (Sonnet 3.5 pricing - needed for accurate vision)
        # $3.00 per 1M input, $15.00 per 1M output
        input_cost = (input_tokens / 1_000_000) * 3.00
        output_cost = (output_tokens / 1_000_000) * 15.00
        total_cost = input_cost + output_cost
        
        logger.info(
            f"Claude API call #{self.total_calls}: "
            f"{input_tokens} in, {output_tokens} out, "
            f"~${total_cost:.4f} this call, "
            f"~${self.estimated_total_cost:.4f} session total"
        )
    
    @property
    def estimated_total_cost(self) -> float:
        """Estimate total session cost (Sonnet 3.5 pricing)."""
        input_cost = (self.total_input_tokens / 1_000_000) * 3.00
        output_cost = (self.total_output_tokens / 1_000_000) * 15.00
        return input_cost + output_cost

usage_tracker = UsageTracker()


@dataclass
class DetectedCard:
    """Card detected from image analysis."""
    name: str
    set_name: Optional[str] = None
    card_number: Optional[str] = None
    language: str = "English"
    variant: str = "Standard"
    condition: str = "Near Mint"
    confidence: float = 0.0
    quantity: int = 1
    needs_confirmation: bool = False
    visible_details: Optional[str] = None  # What AI can see if uncertain
    position: Optional[str] = None  # e.g., "top row, 3rd from left"
    # NEW: Attributes for card matching
    cost: Optional[int] = None  # Card cost (top left number)
    power: Optional[int] = None  # Card power (e.g., 6000)
    color: Optional[str] = None  # Card color (Red, Blue, Green, Purple, Black, Yellow)
    card_type: Optional[str] = None  # Leader, Character, Event, Stage


@dataclass
class ValuationItem:
    """Single item in valuation report."""
    detected: DetectedCard
    matched_name: Optional[str] = None
    unit_price: Optional[float] = None
    line_total: Optional[float] = None
    price_source: str = "PriceCharting"
    found: bool = False


@dataclass
class NegotiationSuggestion:
    """Negotiation recommendation."""
    asking_price: float
    market_value: float
    suggested_offer: float
    max_offer: float
    potential_profit: float
    profit_margin: float
    verdict: str  # "Good Deal", "Fair", "Overpriced", "Great Deal"


@dataclass
class DealAnalysisResult:
    """Complete deal analysis result."""
    items: List[ValuationItem] = field(default_factory=list)
    total_market_value: float = 0.0
    items_found: int = 0
    items_not_found: int = 0
    not_found_items: List[str] = field(default_factory=list)
    asking_price: Optional[float] = None
    negotiation: Optional[NegotiationSuggestion] = None
    analysis_notes: str = ""
    # Confirmation flow fields
    total_cards_detected: int = 0
    cards_needing_confirmation: int = 0
    needs_user_confirmation: bool = False


class DealAnalyzerService:
    """
    Service for analyzing deals using AI and price data.
    
    Workflow:
    1. Receive image(s) + description + asking price
    2. Use Claude to detect and identify cards
    3. Look up prices via PriceCharting
    4. Calculate lot value
    5. Generate negotiation suggestions
    """
    
    # System prompt for card detection - Updated with OCR emphasis
    CARD_DETECTION_PROMPT = """You are an expert trading card identifier. Your job is to READ THE ACTUAL TEXT on the cards, not guess.

CRITICAL: READ THE CARD NUMBERS AND NAMES PRINTED ON EACH CARD.
- One Piece cards have card numbers like "OP01-001", "OP02-034", "OP04-044" printed on them
- The card number is typically in the bottom area of the card
- READ the actual number, don't guess based on artwork

STEP 1: COUNT all cards visible in the image carefully.

STEP 2: For EACH card, READ these values from the actual card:

READ FROM CARD (OCR these values):
- card_number: READ the actual card number printed (e.g., "OP01-003", "OP04-044"). This is CRITICAL.
- name: READ the character name printed on the card
- cost: READ the cost number (top left corner)
- power: READ the power number (bottom left, like 5000, 6000)

OBSERVE FROM CARD:
- position: Location in image (e.g., "top row, 1st from left")  
- color: Card frame color (Red, Blue, Green, Purple, Black, Yellow)
- card_type: "Leader", "Character", "Event", or "Stage"
- variant: "Standard", "Alt-Art", "SP Parallel", or "Manga Art" (look for holo/texture)
- language: "English" or "Japanese"

CONFIDENCE:
- confidence: 0-100 based on how clearly you can READ the card number
- needs_confirmation: true if card number is unclear/unreadable
- visible_details: What you CAN read clearly

ONE PIECE CARD NUMBER LOCATION:
- Card numbers are printed in format "OP0X-XXX" (e.g., OP01-003, OP04-044)
- Usually visible near bottom of card or in the card info area
- SET INDICATOR: OP01=Romance Dawn, OP02=Paramount War, OP03=Pillars of Strength, OP04=Kingdoms of Intrigue, etc.

EXAMPLE - CARD YOU CAN READ CLEARLY:
{
  "position": "top left",
  "card_number": "OP01-003",
  "name": "Monkey D. Luffy",
  "cost": 5,
  "power": 6000,
  "color": "Red",
  "card_type": "Character",
  "set_name": "OP-01 Romance Dawn",
  "language": "English",
  "variant": "Standard",
  "confidence": 95,
  "needs_confirmation": false,
  "visible_details": "Can clearly read OP01-003 and Monkey D. Luffy"
}

EXAMPLE - CARD WITH GLARE/HARD TO READ:
{
  "position": "top middle",
  "card_number": "OP04-???",
  "name": "Kaido(?)",
  "cost": 10,
  "power": 12000,
  "color": "Purple",
  "card_type": "Character",
  "confidence": 40,
  "needs_confirmation": true,
  "visible_details": "Purple card, cost 10, power 12000, can see 'Kaido' but card number obscured by glare"
}

CRITICAL: ONLY OUTPUT VALID JSON. NO TEXT BEFORE OR AFTER.
{"total_cards": <number>, "cards": [<array of card objects>]}"""

    def __init__(
        self,
        anthropic_api_key: Optional[str] = None,
        pricecharting_api_key: Optional[str] = None,
    ):
        """
        Initialize Deal Analyzer service.
        
        Args:
            anthropic_api_key: Claude API key (uses settings if not provided).
            pricecharting_api_key: PriceCharting API key.
        """
        self.anthropic_key = anthropic_api_key or settings.anthropic_api_key
        self.price_service = PriceChartingService(pricecharting_api_key)
        
        if not self.anthropic_key:
            raise ValueError(
                "Anthropic API key not configured. "
                "Set ANTHROPIC_API_KEY in your .env file."
            )
    
    def _detect_image_type(self, image_bytes: bytes) -> str:
        """
        Detect image MIME type from magic bytes.
        
        Args:
            image_bytes: Raw image data.
        
        Returns:
            MIME type string (e.g., "image/jpeg", "image/png").
        """
        # Check magic bytes for common image formats
        if image_bytes[:3] == b'\xff\xd8\xff':
            return "image/jpeg"
        elif image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
            return "image/png"
        elif image_bytes[:6] in (b'GIF87a', b'GIF89a'):
            return "image/gif"
        elif image_bytes[:4] == b'RIFF' and image_bytes[8:12] == b'WEBP':
            return "image/webp"
        elif image_bytes[:4] == b'\x00\x00\x00\x0c' and image_bytes[4:8] == b'jP  ':
            return "image/jp2"  # JPEG 2000
        elif image_bytes[:2] == b'BM':
            return "image/bmp"
        else:
            # Default to JPEG if unknown - Claude will error if wrong
            logger.warning(f"Unknown image type, defaulting to JPEG. First bytes: {image_bytes[:16].hex()}")
            return "image/jpeg"
    
    async def analyze_deal(
        self,
        images: List[bytes],
        description: str = "",
        asking_price: Optional[float] = None,
        category: str = "one-piece",
        expected_count: Optional[int] = None,
    ) -> DealAnalysisResult:
        """
        Analyze a deal with images and description.
        
        Args:
            images: List of image bytes.
            description: Seller's description of the lot.
            asking_price: What the seller is asking.
            category: "one-piece" or "pokemon".
            expected_count: Optional expected number of cards in the lot.
        
        Returns:
            DealAnalysisResult with complete analysis.
        """
        # Step 1: Detect cards using AI
        detection_result = await self._detect_cards(images, description, category, expected_count)
        
        # Handle both old (list) and new (tuple) return formats
        if isinstance(detection_result, tuple):
            total_cards_reported, detected_cards = detection_result
        else:
            detected_cards = detection_result
            total_cards_reported = len(detected_cards)
        
        # Count cards needing confirmation
        cards_needing_conf = sum(1 for c in detected_cards if c.needs_confirmation)
        # ALWAYS require confirmation when analyzing images with multiple cards
        # This ensures users can verify AI accuracy before getting prices
        needs_confirmation = len(detected_cards) > 0
        
        # Step 2: Look up prices for each card (skip uncertain ones for now)
        confirmed_cards = [c for c in detected_cards if not c.needs_confirmation]
        valuation_items = await self._lookup_prices(confirmed_cards, category)
        
        # Add uncertain cards to valuation with no price
        for card in detected_cards:
            if card.needs_confirmation:
                valuation_items.append(ValuationItem(
                    detected=card,
                    found=False,
                ))
        
        # Step 3: Calculate totals
        total_value = sum(
            item.line_total for item in valuation_items 
            if item.line_total is not None
        )
        items_found = sum(1 for item in valuation_items if item.found)
        not_found = [
            item.detected.name for item in valuation_items if not item.found
        ]
        
        # Step 4: Generate negotiation suggestions
        negotiation = None
        if asking_price is not None and total_value > 0:
            negotiation = self._generate_negotiation(asking_price, total_value)
        
        # Step 5: Generate analysis notes (with confirmation info)
        notes = self._generate_notes(
            valuation_items, total_value, asking_price, len(not_found)
        )
        
        if needs_confirmation:
            notes = f"⚠️ {cards_needing_conf} card(s) need your confirmation. " + notes
        
        return DealAnalysisResult(
            items=valuation_items,
            total_market_value=total_value,
            items_found=items_found,
            items_not_found=len(not_found),
            not_found_items=not_found,
            asking_price=asking_price,
            negotiation=negotiation,
            analysis_notes=notes,
            total_cards_detected=total_cards_reported,
            cards_needing_confirmation=cards_needing_conf,
            needs_user_confirmation=needs_confirmation,
        )
    
    async def _detect_cards(
        self,
        images: List[bytes],
        description: str,
        category: str,
        expected_count: Optional[int] = None,
    ) -> List[DetectedCard]:
        """
        Detect cards from images and/or description.
        
        Cost optimization:
        - If only description provided: Use text-only parsing (cheaper)
        - If images provided: Use vision API
        """
        # If no images, try to parse from description only (FREE - no API call)
        if not images and description:
            return self._parse_description_only(description, category)
        
        client = anthropic.Anthropic(api_key=self.anthropic_key)
        
        # Build message content with images
        content = []
        
        for i, image_bytes in enumerate(images):
            # Encode image to base64
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            
            # Determine media type from magic bytes
            media_type = self._detect_image_type(image_bytes)
            
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": image_b64,
                },
            })
        
        # Add text context with expected count
        context = f"Category: {category.upper()} cards\n"
        if expected_count and expected_count > 0:
            context += f"IMPORTANT: User says there are {expected_count} cards in this lot. Please identify each one.\n"
        if description:
            context += f"Seller Description: {description}\n"
        context += "\nPlease identify all cards visible in the image(s). Go through each card position carefully."
        
        content.append({"type": "text", "text": context})
        
        print(f"\n=== DETECT_CARDS ===")
        print(f"Expected count: {expected_count}")
        print(f"Context: {context}")
        
        # Call Claude - using Haiku (fastest, cheapest)
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=4096,
            system=self.CARD_DETECTION_PROMPT,
            messages=[{"role": "user", "content": content}],
        )
        
        # Track usage for cost monitoring
        usage_tracker.log_call(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
        
        # Log Claude's raw response for debugging
        raw_response = response.content[0].text
        print(f"\n=== CLAUDE RAW RESPONSE ===")
        print(raw_response[:3000])  # First 3000 chars
        print(f"=== END CLAUDE RESPONSE ===\n")
        
        # Parse response - returns (total_count, cards_list)
        result = self._parse_card_detection(raw_response)
        print(f"PARSING RESULT: {result[0]} cards reported, {len(result[1])} cards parsed")
        for i, card in enumerate(result[1]):
            attrs = f"cost={card.cost}, power={card.power}, color={card.color}"
            print(f"  Card {i+1}: {card.name} ({attrs}, conf: {card.confidence:.0%}, needs_conf: {card.needs_confirmation})")
        
        return result
    
    def _parse_description_only(
        self,
        description: str,
        category: str,
    ) -> tuple[int, List[DetectedCard]]:
        """
        Parse card names from text description without API call.
        
        This is FREE - no Claude API usage.
        Works for simple descriptions like:
        - "Roronoa Zoro SP, Monkey D Luffy"
        - "2x Charizard, 3x Pikachu"
        
        Returns:
            Tuple of (total_count, list of cards)
        """
        import re
        
        cards = []
        
        # Split by common separators
        parts = re.split(r'[,\n;]+', description)
        
        for part in parts:
            part = part.strip()
            if not part or len(part) < 3:
                continue
            
            # Check for quantity prefix like "2x", "3x", "x2"
            quantity = 1
            qty_match = re.match(r'^(\d+)\s*[xX]\s*(.+)$', part)
            if qty_match:
                quantity = int(qty_match.group(1))
                part = qty_match.group(2).strip()
            else:
                qty_match = re.match(r'^(.+)\s*[xX]\s*(\d+)$', part)
                if qty_match:
                    part = qty_match.group(1).strip()
                    quantity = int(qty_match.group(2))
            
            # Detect variant hints
            variant = "Standard"
            part_lower = part.lower()
            if "sp" in part_lower or "parallel" in part_lower:
                variant = "SP Parallel"
            elif "alt" in part_lower or "alternate" in part_lower:
                variant = "Alt-Art"
            elif "manga" in part_lower:
                variant = "Manga Art"
            
            cards.append(DetectedCard(
                name=part,
                variant=variant,
                quantity=quantity,
                confidence=0.6,  # Lower confidence since not AI-verified
            ))
        
        return len(cards), cards
    
    def _parse_card_detection(self, response_text: str) -> tuple[int, List[DetectedCard]]:
        """
        Parse Claude's card detection response.
        
        Returns:
            Tuple of (total_cards_reported, list of detected cards)
        """
        import json
        import re
        
        cards = []
        total_reported = 0
        
        print(f"PARSING: Response length = {len(response_text)} chars")
        
        # Try to extract JSON object with total_cards and cards array
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        print(f"PARSING: JSON object match found = {json_match is not None}")
        
        if json_match:
            try:
                matched_json = json_match.group()
                print(f"PARSING: Matched JSON = {matched_json[:500]}...")
                data = json.loads(matched_json)
                total_reported = data.get("total_cards", 0)
                card_data = data.get("cards", [])
                print(f"PARSING: total_cards={total_reported}, cards array length={len(card_data)}")
                
                for card in card_data:
                    confidence = float(card.get("confidence", 50)) / 100.0
                    needs_conf = card.get("needs_confirmation", False)
                    
                    # Auto-flag low confidence cards
                    if confidence < 0.6:
                        needs_conf = True
                    
                    # Parse cost and power as integers
                    cost_val = card.get("cost")
                    if cost_val is not None:
                        try:
                            cost_val = int(str(cost_val).strip())
                        except (ValueError, TypeError):
                            cost_val = None
                    
                    power_val = card.get("power")
                    if power_val is not None:
                        try:
                            # Handle "6000+" or "6000" format
                            power_val = int(str(power_val).replace("+", "").replace("-", "").strip())
                        except (ValueError, TypeError):
                            power_val = None
                    
                    cards.append(DetectedCard(
                        name=card.get("name", "Unknown Card"),
                        set_name=card.get("set_name", card.get("set")),
                        card_number=card.get("card_number", card.get("number")),
                        language=card.get("language", "English"),
                        variant=card.get("variant", "Standard"),
                        condition=card.get("condition", "Near Mint"),
                        confidence=confidence,
                        quantity=int(card.get("quantity", 1)),
                        needs_confirmation=needs_conf,
                        visible_details=card.get("visible_details"),
                        position=card.get("position"),
                        # NEW: Card attributes for matching
                        cost=cost_val,
                        power=power_val,
                        color=card.get("color"),
                        card_type=card.get("card_type", card.get("type")),
                    ))
            except json.JSONDecodeError as e:
                print(f"PARSING ERROR: JSON decode failed: {e}")
                print(f"PARSING ERROR: Problematic JSON: {json_match.group()[:500]}...")
        
        # Fallback: try old array format
        if not cards:
            print("PARSING: No cards from object format, trying array format...")
            json_match = re.search(r'\[[\s\S]*\]', response_text)
            print(f"PARSING: Array match found = {json_match is not None}")
            if json_match:
                try:
                    card_data = json.loads(json_match.group())
                    total_reported = len(card_data)
                    print(f"PARSING: Array contained {len(card_data)} cards")
                    for card in card_data:
                        confidence = float(card.get("confidence", card.get("Confidence", 50))) / 100.0
                        
                        # Parse cost and power
                        cost_val = card.get("cost")
                        if cost_val is not None:
                            try:
                                cost_val = int(str(cost_val).strip())
                            except (ValueError, TypeError):
                                cost_val = None
                        
                        power_val = card.get("power")
                        if power_val is not None:
                            try:
                                power_val = int(str(power_val).replace("+", "").replace("-", "").strip())
                            except (ValueError, TypeError):
                                power_val = None
                        
                        cards.append(DetectedCard(
                            name=card.get("name", card.get("Card Name", "Unknown")),
                            set_name=card.get("set", card.get("Set Name")),
                            card_number=card.get("number", card.get("Card Number")),
                            language=card.get("language", card.get("Language", "English")),
                            variant=card.get("variant", card.get("Variant", "Standard")),
                            condition=card.get("condition", card.get("Condition", "Near Mint")),
                            confidence=confidence,
                            quantity=int(card.get("quantity", card.get("Quantity", 1))),
                            needs_confirmation=confidence < 0.6,
                            cost=cost_val,
                            power=power_val,
                            color=card.get("color"),
                            card_type=card.get("card_type", card.get("type")),
                        ))
                except json.JSONDecodeError as e:
                    print(f"PARSING ERROR: Array JSON decode failed: {e}")
        
        if not cards:
            print(f"PARSING WARNING: No cards parsed! Full response:\n{response_text}")
        
        print(f"PARSING COMPLETE: Returning {total_reported} reported, {len(cards)} parsed")
        return total_reported, cards
    
    async def _lookup_prices(
        self,
        cards: List[DetectedCard],
        category: str,
    ) -> List[ValuationItem]:
        """Look up prices for detected cards."""
        pc_category = ProductCategory.TRADING_CARDS
        
        valuation_items = []
        
        for card in cards:
            # Build search query
            search_name = card.name
            if card.set_name:
                search_name = f"{card.name} {card.set_name}"
            
            # Look up price
            price_result = await self.price_service.get_price_by_name(
                search_name, pc_category
            )
            
            if price_result and price_result.best_price:
                unit_price = price_result.best_price
                line_total = unit_price * card.quantity
                
                valuation_items.append(ValuationItem(
                    detected=card,
                    matched_name=price_result.product_name,
                    unit_price=unit_price,
                    line_total=line_total,
                    found=True,
                ))
            else:
                valuation_items.append(ValuationItem(
                    detected=card,
                    found=False,
                ))
        
        return valuation_items
    
    def _generate_negotiation(
        self,
        asking_price: float,
        market_value: float,
    ) -> NegotiationSuggestion:
        """Generate negotiation recommendations."""
        # Calculate ratios
        ratio = asking_price / market_value if market_value > 0 else 999
        
        # Determine verdict and suggestions
        if ratio <= 0.5:
            verdict = "Great Deal"
            suggested_offer = asking_price  # Take it!
            max_offer = asking_price * 1.1
        elif ratio <= 0.7:
            verdict = "Good Deal"
            suggested_offer = asking_price * 0.9
            max_offer = asking_price
        elif ratio <= 0.9:
            verdict = "Fair"
            suggested_offer = market_value * 0.65
            max_offer = market_value * 0.75
        else:
            verdict = "Overpriced"
            suggested_offer = market_value * 0.5
            max_offer = market_value * 0.65
        
        potential_profit = market_value - suggested_offer
        profit_margin = (potential_profit / suggested_offer * 100) if suggested_offer > 0 else 0
        
        return NegotiationSuggestion(
            asking_price=asking_price,
            market_value=market_value,
            suggested_offer=round(suggested_offer, 2),
            max_offer=round(max_offer, 2),
            potential_profit=round(potential_profit, 2),
            profit_margin=round(profit_margin, 1),
            verdict=verdict,
        )
    
    def _generate_notes(
        self,
        items: List[ValuationItem],
        total_value: float,
        asking_price: Optional[float],
        not_found_count: int,
    ) -> str:
        """Generate analysis notes."""
        notes = []
        
        if not_found_count > 0:
            notes.append(
                f"⚠️ {not_found_count} item(s) could not be priced. "
                "Manual verification recommended."
            )
        
        # Find high-value items
        high_value = [i for i in items if i.unit_price and i.unit_price > 50]
        if high_value:
            notes.append(
                f"💎 {len(high_value)} high-value item(s) detected. "
                "Verify variants carefully."
            )
        
        # Price comparison
        if asking_price and total_value > 0:
            ratio = asking_price / total_value
            if ratio < 0.6:
                notes.append("🔥 Asking price is significantly below market value!")
            elif ratio > 1.1:
                notes.append("📊 Asking price is above market value. Negotiate down.")
        
        return " ".join(notes) if notes else "Analysis complete."


async def quick_analyze(
    image_bytes: bytes,
    description: str = "",
    asking_price: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Quick analysis function for single image.
    
    Args:
        image_bytes: Image data.
        description: Optional description.
        asking_price: Optional asking price.
    
    Returns:
        Dict with analysis results.
    """
    service = DealAnalyzerService()
    result = await service.analyze_deal(
        images=[image_bytes],
        description=description,
        asking_price=asking_price,
    )
    
    return {
        "total_value": result.total_market_value,
        "items_found": result.items_found,
        "items_not_found": result.items_not_found,
        "items": [
            {
                "name": item.detected.name,
                "matched": item.matched_name,
                "price": item.unit_price,
                "quantity": item.detected.quantity,
                "total": item.line_total,
            }
            for item in result.items
        ],
        "negotiation": {
            "verdict": result.negotiation.verdict,
            "suggested_offer": result.negotiation.suggested_offer,
            "max_offer": result.negotiation.max_offer,
            "potential_profit": result.negotiation.potential_profit,
        } if result.negotiation else None,
        "notes": result.analysis_notes,
    }
