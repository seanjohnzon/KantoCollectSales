"""
Listing Scraper Service.

Fetches listing data from eBay and Facebook Marketplace URLs.
"""

import re
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import httpx


class ListingScraperService:
    """
    Service to scrape listing data from marketplace URLs.
    
    Supports:
    - eBay listings
    - Facebook Marketplace listings
    """
    
    def __init__(self):
        """Initialize the scraper service."""
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
    
    async def fetch_listing(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Fetch and parse listing data from URL.
        
        Args:
            url: eBay or Facebook Marketplace URL.
        
        Returns:
            Dict with listing data (title, price, description, image_url, etc.)
            or None if parsing fails.
        """
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        if "ebay.com" in domain:
            return await self._fetch_ebay(url)
        elif "facebook.com" in domain and "marketplace" in url.lower():
            return await self._fetch_facebook(url)
        else:
            raise ValueError(f"Unsupported marketplace: {domain}")
    
    async def _fetch_ebay(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Fetch eBay listing data.
        
        Uses eBay's HTML page and extracts data from structured data tags.
        
        Args:
            url: eBay listing URL.
        
        Returns:
            Parsed listing data.
        """
        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.get(url, headers=self.headers, timeout=15.0)
                response.raise_for_status()
                html = response.text
            except httpx.HTTPError as e:
                raise ValueError(f"Failed to fetch eBay listing: {str(e)}")
        
        result = {
            "source": "eBay",
            "title": None,
            "description": None,
            "price": None,
            "image_url": None,
            "seller": None,
            "location": None,
        }
        
        # Extract title from og:title or h1
        title_match = re.search(r'<meta property="og:title" content="([^"]+)"', html)
        if title_match:
            result["title"] = self._clean_html(title_match.group(1))
        else:
            h1_match = re.search(r'<h1[^>]*class="[^"]*x-item-title[^"]*"[^>]*>([^<]+)</h1>', html)
            if h1_match:
                result["title"] = self._clean_html(h1_match.group(1))
        
        # Extract price - eBay has several price formats
        # Try priceCurrency and price from schema
        price_match = re.search(r'"price":\s*"?([\d.]+)"?', html)
        if price_match:
            try:
                result["price"] = float(price_match.group(1))
            except ValueError:
                pass
        
        # Fallback: look for price in visible text
        if not result["price"]:
            price_text = re.search(r'US \$([0-9,]+\.\d{2})', html)
            if price_text:
                try:
                    result["price"] = float(price_text.group(1).replace(",", ""))
                except ValueError:
                    pass
        
        # Extract image
        img_match = re.search(r'<meta property="og:image" content="([^"]+)"', html)
        if img_match:
            result["image_url"] = img_match.group(1)
        else:
            # Try to find the main product image
            img_alt = re.search(r'<img[^>]*class="[^"]*ux-image-carousel[^"]*"[^>]*src="([^"]+)"', html)
            if img_alt:
                result["image_url"] = img_alt.group(1)
        
        # Extract description (from og:description)
        desc_match = re.search(r'<meta property="og:description" content="([^"]+)"', html)
        if desc_match:
            result["description"] = self._clean_html(desc_match.group(1))
        
        # Extract seller name
        seller_match = re.search(r'<span[^>]*class="[^"]*ux-seller-section__item--seller[^"]*"[^>]*>([^<]+)</span>', html)
        if seller_match:
            result["seller"] = self._clean_html(seller_match.group(1))
        
        # Extract location
        location_match = re.search(r'<span[^>]*itemprop="availableAtOrFrom"[^>]*>([^<]+)</span>', html)
        if location_match:
            result["location"] = self._clean_html(location_match.group(1))
        
        return result
    
    async def _fetch_facebook(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Fetch Facebook Marketplace listing data.
        
        Note: Facebook requires authentication for most marketplace data.
        This method extracts what's publicly available.
        
        Args:
            url: Facebook Marketplace listing URL.
        
        Returns:
            Parsed listing data (may be limited without login).
        """
        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.get(url, headers=self.headers, timeout=15.0)
                response.raise_for_status()
                html = response.text
            except httpx.HTTPError as e:
                raise ValueError(f"Failed to fetch Facebook listing: {str(e)}")
        
        result = {
            "source": "Facebook Marketplace",
            "title": None,
            "description": None,
            "price": None,
            "image_url": None,
            "seller": None,
            "location": None,
        }
        
        # Extract title from og:title
        title_match = re.search(r'<meta property="og:title" content="([^"]+)"', html)
        if title_match:
            title = self._clean_html(title_match.group(1))
            # Facebook often includes price in title like "$50 · Item Name"
            if " · " in title:
                parts = title.split(" · ", 1)
                if parts[0].startswith("$"):
                    try:
                        result["price"] = float(parts[0].replace("$", "").replace(",", ""))
                    except ValueError:
                        pass
                    result["title"] = parts[1] if len(parts) > 1 else title
                else:
                    result["title"] = title
            else:
                result["title"] = title
        
        # Extract image from og:image
        img_match = re.search(r'<meta property="og:image" content="([^"]+)"', html)
        if img_match:
            result["image_url"] = img_match.group(1)
        
        # Extract description from og:description
        desc_match = re.search(r'<meta property="og:description" content="([^"]+)"', html)
        if desc_match:
            result["description"] = self._clean_html(desc_match.group(1))
        
        # Note: Most Facebook Marketplace data requires login
        # We can only get limited public data from meta tags
        
        return result
    
    def _clean_html(self, text: str) -> str:
        """
        Clean HTML entities and extra whitespace from text.
        
        Args:
            text: Text to clean.
        
        Returns:
            Cleaned text.
        """
        import html
        text = html.unescape(text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
