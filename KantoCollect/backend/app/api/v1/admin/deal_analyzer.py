"""
Deal Analyzer API endpoints.

Admin-only endpoints for analyzing card lots and getting valuations.
"""

from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.api.deps import AdminUser
from app.services.deal_analyzer.service import DealAnalyzerService
from app.services.price_lookup.pricecharting import (
    PriceChartingService,
    ProductCategory,
)


router = APIRouter()


# Response Models
class DetectedCardResponse(BaseModel):
    """Detected card info."""
    name: str
    set_name: Optional[str] = None
    card_number: Optional[str] = None
    language: str = "English"
    variant: str = "Standard"
    condition: str = "Near Mint"
    confidence: float = 0.0
    quantity: int = 1
    needs_confirmation: bool = False
    visible_details: Optional[str] = None
    position: Optional[str] = None


class ValuationItemResponse(BaseModel):
    """Single item valuation."""
    detected: DetectedCardResponse
    matched_name: Optional[str] = None
    unit_price: Optional[float] = None
    line_total: Optional[float] = None
    price_source: str = "PriceCharting"
    found: bool = False


class NegotiationResponse(BaseModel):
    """Negotiation suggestion."""
    asking_price: float
    market_value: float
    suggested_offer: float
    max_offer: float
    potential_profit: float
    profit_margin: float
    verdict: str


class DealAnalysisResponse(BaseModel):
    """Complete deal analysis response."""
    items: List[ValuationItemResponse]
    total_market_value: float
    items_found: int
    items_not_found: int
    not_found_items: List[str]
    asking_price: Optional[float] = None
    negotiation: Optional[NegotiationResponse] = None
    analysis_notes: str


class PriceSearchResponse(BaseModel):
    """Price search result."""
    product_id: str
    product_name: str
    category: str
    loose_price: Optional[float] = None
    cib_price: Optional[float] = None
    new_price: Optional[float] = None
    graded_price: Optional[float] = None


class QuickPriceRequest(BaseModel):
    """Request for quick price lookup."""
    product_name: str
    category: Optional[str] = "trading-cards"


class FetchListingRequest(BaseModel):
    """Request to fetch a listing from URL."""
    url: str


class FetchListingResponse(BaseModel):
    """Response with fetched listing data."""
    source: str
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    image_url: Optional[str] = None
    seller: Optional[str] = None
    location: Optional[str] = None


# Endpoints

@router.post("/analyze")
async def analyze_deal(
    current_user: AdminUser,
    image: Optional[UploadFile] = File(default=None, description="Image of the card lot"),
    description: str = Form(default="", description="Seller's description"),
    asking_price: Optional[float] = Form(default=None, description="Asking price"),
    category: str = Form(default="one-piece", description="Card category"),
    expected_count: Optional[int] = Form(default=None, description="Expected number of cards"),
):
    """
    Analyze a card lot deal.
    
    Upload an image of cards and/or provide description and asking price.
    Returns AI-detected cards with market values and negotiation suggestions.
    
    Args:
        image: Optional image of the card lot.
        description: Optional seller description for context.
        asking_price: Optional asking price for negotiation suggestions.
        category: "one-piece" or "pokemon".
        expected_count: Optional expected number of cards in the lot.
    
    Returns:
        Simplified analysis with cards, total_value, and negotiation tips.
    """
    try:
        # Require either image or description
        if not image and not description:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please provide an image or description",
            )
        
        # Read image bytes if provided
        image_bytes_list = []
        if image:
            content = await image.read()
            if len(content) > 10 * 1024 * 1024:  # 10MB limit
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Image exceeds 10MB limit",
                )
            image_bytes_list.append(content)
        
        # Run analysis
        service = DealAnalyzerService()
        result = await service.analyze_deal(
            images=image_bytes_list,
            description=description,
            asking_price=asking_price,
            category=category,
            expected_count=expected_count,
        )
        
        # Return simplified format for frontend
        cards = []
        for item in result.items:
            card = {
                "name": item.matched_name or item.detected.name,
                "set": item.detected.set_name or "Unknown Set",
                "number": item.detected.card_number or "",
                "language": item.detected.language,
                "variant": item.detected.variant,
                "price": item.unit_price or 0,
                "confidence": int(item.detected.confidence * 100),
                "needs_confirmation": item.detected.needs_confirmation,
                "visible_details": item.detected.visible_details,
                "position": item.detected.position,
            }
            cards.append(card)
        
        return {
            "cards": cards,
            "total_value": result.total_market_value,
            "items_found": result.items_found,
            "items_not_found": result.items_not_found,
            "asking_price": result.asking_price,
            "verdict": result.negotiation.verdict if result.negotiation else None,
            "suggested_offer": result.negotiation.suggested_offer if result.negotiation else None,
            "notes": result.analysis_notes,
            # Card count verification
            "expected_count": expected_count,
            "total_cards_detected": result.total_cards_detected,
            "cards_needing_confirmation": result.cards_needing_confirmation,
            "needs_user_confirmation": result.needs_user_confirmation,
            "count_match": expected_count is None or expected_count == result.total_cards_detected,
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}",
        )


@router.post("/price-lookup", response_model=PriceSearchResponse)
async def lookup_price(
    current_user: AdminUser,
    request: QuickPriceRequest,
):
    """
    Quick price lookup by product name.
    
    Search PriceCharting for a product and return current prices.
    
    Args:
        request: Product name and optional category.
    
    Returns:
        Price information for the product.
    """
    try:
        service = PriceChartingService()
        
        # Map category string to enum
        category = None
        if request.category:
            try:
                category = ProductCategory(request.category)
            except ValueError:
                category = ProductCategory.TRADING_CARDS
        
        result = await service.get_price_by_name(
            request.product_name,
            category,
        )
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product not found: {request.product_name}",
            )
        
        return PriceSearchResponse(
            product_id=result.product_id,
            product_name=result.product_name,
            category=result.console_name,
            loose_price=result.loose_price,
            cib_price=result.cib_price,
            new_price=result.new_price,
            graded_price=result.graded_price,
        )
    
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Price lookup failed: {str(e)}",
        )


@router.get("/price-lookup/upc/{upc}", response_model=PriceSearchResponse)
async def lookup_price_by_upc(
    current_user: AdminUser,
    upc: str,
):
    """
    Look up product price by UPC barcode.
    
    Useful for scanning sealed products.
    
    Args:
        upc: UPC barcode string.
    
    Returns:
        Price information for the product.
    """
    try:
        service = PriceChartingService()
        result = await service.get_price_by_upc(upc)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product not found for UPC: {upc}",
            )
        
        return PriceSearchResponse(
            product_id=result.product_id,
            product_name=result.product_name,
            category=result.console_name,
            loose_price=result.loose_price,
            cib_price=result.cib_price,
            new_price=result.new_price,
            graded_price=result.graded_price,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"UPC lookup failed: {str(e)}",
        )


@router.get("/search/{query}")
async def search_products(
    current_user: AdminUser,
    query: str,
    category: Optional[str] = None,
    limit: int = 10,
):
    """
    Search for products in PriceCharting.
    
    Args:
        query: Search query.
        category: Optional category filter.
        limit: Maximum results (default 10).
    
    Returns:
        List of matching products.
    """
    try:
        service = PriceChartingService()
        
        # Map category
        pc_category = None
        if category:
            try:
                pc_category = ProductCategory(category)
            except ValueError:
                pass
        
        results = await service.search_products(query, pc_category)
        
        # Limit results
        return {
            "query": query,
            "count": min(len(results), limit),
            "products": results[:limit],
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        )


@router.post("/fetch-listing", response_model=FetchListingResponse)
async def fetch_listing(
    current_user: AdminUser,
    request: FetchListingRequest,
):
    """
    Fetch listing data from eBay or Facebook Marketplace URL.
    
    Extracts title, description, price, and images from the listing.
    
    Args:
        request: URL of the listing.
    
    Returns:
        Extracted listing data.
    """
    from app.services.deal_analyzer.listing_scraper import ListingScraperService
    
    try:
        service = ListingScraperService()
        result = await service.fetch_listing(request.url)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extract listing data from URL",
            )
        
        return FetchListingResponse(
            source=result.get("source", "Unknown"),
            url=request.url,
            title=result.get("title"),
            description=result.get("description"),
            price=result.get("price"),
            image_url=result.get("image_url"),
            seller=result.get("seller"),
            location=result.get("location"),
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch listing: {str(e)}",
        )
