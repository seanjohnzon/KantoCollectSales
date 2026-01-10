"""
PriceCharting API integration service.

Provides price lookups, lot valuation, and deal alerts functionality.
Documentation: https://www.pricecharting.com/api-documentation
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

import httpx

from app.core.config import settings


class ProductCategory(str, Enum):
    """PriceCharting product categories."""
    VIDEO_GAMES = "video-games"
    TRADING_CARDS = "trading-cards"
    TOYS = "toys"
    COMICS = "comics"


@dataclass
class PriceResult:
    """Price lookup result."""
    product_id: str
    product_name: str
    console_name: str  # Category/Set name
    loose_price: Optional[float] = None
    cib_price: Optional[float] = None  # Complete in Box
    new_price: Optional[float] = None
    graded_price: Optional[float] = None
    box_only_price: Optional[float] = None
    manual_only_price: Optional[float] = None
    currency: str = "USD"
    
    @property
    def best_price(self) -> Optional[float]:
        """Get the most relevant price (prioritize loose for singles)."""
        return self.loose_price or self.cib_price or self.new_price


@dataclass
class LotItem:
    """Item in a lot for valuation."""
    product_name: str
    quantity: int = 1
    condition: str = "loose"  # loose, cib, new, graded


@dataclass
class LotValuation:
    """Result of lot valuation."""
    items: List[Dict[str, Any]]
    total_value: float
    item_count: int
    found_count: int
    not_found: List[str]


class PriceChartingService:
    """
    Service for interacting with PriceCharting API.
    
    Requires Legendary subscription for API access.
    """
    
    BASE_URL = "https://www.pricecharting.com/api"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize PriceCharting service.
        
        Args:
            api_key: PriceCharting API key. Uses settings if not provided.
        """
        self.api_key = api_key or settings.pricecharting_api_key
        if not self.api_key:
            raise ValueError(
                "PriceCharting API key not configured. "
                "Set PRICECHARTING_API_KEY in your .env file."
            )
    
    async def _request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Make authenticated request to PriceCharting API.
        
        Args:
            endpoint: API endpoint path.
            params: Query parameters.
        
        Returns:
            Dict: JSON response data, or None if not found/error.
        """
        url = f"{self.BASE_URL}/{endpoint}"
        
        # Add API key to params
        request_params = {"t": self.api_key}
        if params:
            request_params.update(params)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=request_params, timeout=30.0)
                
                # Handle 404 gracefully - product not found
                if response.status_code == 404:
                    return None
                
                # Handle other errors
                if response.status_code >= 400:
                    print(f"PriceCharting API error: {response.status_code} for {url}")
                    return None
                
                return response.json()
        except Exception as e:
            print(f"PriceCharting API request failed: {e}")
            return None
    
    async def search_products(
        self,
        query: str,
        category: Optional[ProductCategory] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for products by name.
        
        Args:
            query: Search query string.
            category: Optional category filter.
        
        Returns:
            List of matching products (empty list if not found/error).
        
        Example:
            >>> service = PriceChartingService()
            >>> results = await service.search_products("Charizard")
        """
        params = {"q": query}
        if category:
            params["type"] = category.value
        
        data = await self._request("products", params)
        if data is None:
            return []
        return data.get("products", [])
    
    async def get_product_price(self, product_id: str) -> Optional[PriceResult]:
        """
        Get current prices for a specific product.
        
        Args:
            product_id: PriceCharting product ID.
        
        Returns:
            PriceResult with current prices, or None if not found.
        """
        data = await self._request("product", {"id": product_id})
        
        if data is None:
            return None
        
        return PriceResult(
            product_id=str(data.get("id", product_id)),
            product_name=data.get("product-name", ""),
            console_name=data.get("console-name", ""),
            loose_price=self._parse_price(data.get("loose-price")),
            cib_price=self._parse_price(data.get("cib-price")),
            new_price=self._parse_price(data.get("new-price")),
            graded_price=self._parse_price(data.get("graded-price")),
            box_only_price=self._parse_price(data.get("box-only-price")),
            manual_only_price=self._parse_price(data.get("manual-only-price")),
        )
    
    async def get_price_by_name(
        self,
        product_name: str,
        category: Optional[ProductCategory] = None,
    ) -> Optional[PriceResult]:
        """
        Search for a product and get its price.
        
        Args:
            product_name: Name to search for.
            category: Optional category filter.
        
        Returns:
            PriceResult for best match, or None if not found.
        """
        products = await self.search_products(product_name, category)
        
        if not products:
            return None
        
        # Get the first (best) match
        best_match = products[0]
        return await self.get_product_price(str(best_match.get("id")))
    
    async def get_price_by_upc(self, upc: str) -> Optional[PriceResult]:
        """
        Look up product price by UPC/barcode.
        
        Args:
            upc: UPC barcode string.
        
        Returns:
            PriceResult if found, None otherwise.
        """
        data = await self._request("product", {"upc": upc})
        
        if data is None:
            return None
        
        return PriceResult(
            product_id=str(data.get("id", "")),
            product_name=data.get("product-name", ""),
            console_name=data.get("console-name", ""),
            loose_price=self._parse_price(data.get("loose-price")),
            cib_price=self._parse_price(data.get("cib-price")),
            new_price=self._parse_price(data.get("new-price")),
            graded_price=self._parse_price(data.get("graded-price")),
        )
    
    async def calculate_lot_value(
        self,
        items: List[LotItem],
        category: Optional[ProductCategory] = None,
    ) -> LotValuation:
        """
        Calculate total value of a lot of items.
        
        Args:
            items: List of items to value.
            category: Category for searches.
        
        Returns:
            LotValuation with breakdown and totals.
        
        Example:
            >>> items = [
            ...     LotItem("Charizard Base Set", quantity=1),
            ...     LotItem("Pikachu Promo", quantity=2),
            ... ]
            >>> valuation = await service.calculate_lot_value(items)
        """
        valued_items = []
        not_found = []
        total_value = 0.0
        
        for item in items:
            price_result = await self.get_price_by_name(
                item.product_name,
                category
            )
            
            if price_result and price_result.best_price:
                # Get price based on condition
                if item.condition == "cib":
                    item_price = price_result.cib_price or price_result.loose_price
                elif item.condition == "new":
                    item_price = price_result.new_price or price_result.cib_price
                elif item.condition == "graded":
                    item_price = price_result.graded_price
                else:
                    item_price = price_result.loose_price
                
                if item_price:
                    line_total = item_price * item.quantity
                    total_value += line_total
                    
                    valued_items.append({
                        "name": item.product_name,
                        "matched_name": price_result.product_name,
                        "quantity": item.quantity,
                        "condition": item.condition,
                        "unit_price": item_price,
                        "line_total": line_total,
                        "product_id": price_result.product_id,
                        "console": price_result.console_name,
                    })
                else:
                    not_found.append(item.product_name)
            else:
                not_found.append(item.product_name)
        
        return LotValuation(
            items=valued_items,
            total_value=total_value,
            item_count=len(items),
            found_count=len(valued_items),
            not_found=not_found,
        )
    
    @staticmethod
    def _parse_price(value: Any) -> Optional[float]:
        """Parse price value from API response."""
        if value is None:
            return None
        try:
            # PriceCharting returns prices in cents
            return float(value) / 100.0
        except (TypeError, ValueError):
            return None


# Convenience function for quick lookups
async def quick_price_lookup(product_name: str) -> Optional[Dict[str, Any]]:
    """
    Quick price lookup without instantiating service.
    
    Args:
        product_name: Name of product to look up.
    
    Returns:
        Dict with price info or None.
    """
    try:
        service = PriceChartingService()
        result = await service.get_price_by_name(product_name)
        
        if result:
            return {
                "name": result.product_name,
                "category": result.console_name,
                "loose_price": result.loose_price,
                "cib_price": result.cib_price,
                "new_price": result.new_price,
            }
        return None
    except Exception:
        return None
