"""
Web Scraper - Advanced content extraction
"""
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup
import markdownify
from app.models.vpn_manager import vpn_manager


class WebScraper:
    def __init__(self):
        self.vpn = vpn_manager

    async def scrape_article(self, url: str) -> Dict[str, Any]:
        result = await self.vpn.scrape_website(
            url, extract_text=True, extract_images=True, extract_links=True
        )
        if not result.get("success", True):
            return result

        soup = BeautifulSoup(result.get("content", ""), "html.parser")

        return {
            "url": url, "title": result.get("title"),
            "author": self._extract_author(soup),
            "publish_date": self._extract_date(soup),
            "content": result.get("text_content", ""),
            "summary": self._generate_summary(result.get("text_content", "")),
            "images": result.get("images", []),
            "links": result.get("links", []),
            "reading_time": self._estimate_reading_time(result.get("text_content", "")),
            "proxy_used": result.get("proxy_used"),
            "latency_ms": result.get("latency_ms")
        }

    async def scrape_product(self, url: str) -> Dict[str, Any]:
        result = await self.vpn.scrape_website(url, extract_text=True, extract_images=True)
        if not result.get("success", True):
            return result

        soup = BeautifulSoup(result.get("content", ""), "html.parser")

        return {
            "url": url, "title": result.get("title"),
            "price": self._extract_price(soup),
            "currency": self._extract_currency(soup),
            "description": self._extract_description(soup),
            "images": [img["src"] for img in result.get("images", [])[:5]],
            "availability": self._extract_availability(soup),
            "rating": self._extract_rating(soup),
            "reviews_count": self._extract_reviews_count(soup),
            "specifications": self._extract_specifications(soup)
        }

    async def convert_to_markdown(self, url: str) -> Dict[str, Any]:
        result = await self.vpn.fetch_url(url)
        if not result.get("success", True):
            return result

        markdown = markdownify.markdownify(result["content"], heading_style="ATX")
        return {
            "success": True, "url": url, "markdown": markdown,
            "title": result.get("title"), "proxy_used": result.get("proxy_used")
        }

    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        selectors = ["[rel=author]", ".author", ".byline", "[class*=author]", "meta[name=author]"]
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get("content") if element.name == "meta" else element.get_text(strip=True)
        return None

    def _extract_date(self, soup: BeautifulSoup) -> Optional[str]:
        date_meta = soup.find("meta", property="article:published_time")
        if date_meta:
            return date_meta.get("content")
        time_element = soup.find("time")
        if time_element:
            return time_element.get("datetime") or time_element.get_text(strip=True)
        return None

    def _generate_summary(self, text: str, max_length: int = 300) -> str:
        if len(text) <= max_length:
            return text
        return text[:max_length].rsplit(" ", 1)[0] + "..."

    def _estimate_reading_time(self, text: str) -> int:
        return max(1, len(text.split()) // 200)

    def _extract_price(self, soup: BeautifulSoup) -> Optional[str]:
        for selector in ["[class*=price]", "[class*=cost]", "[id*=price]", ".product-price", "meta[property=product:price:amount]"]:
            element = soup.select_one(selector)
            if element:
                return element.get("content") if element.name == "meta" else element.get_text(strip=True)
        return None

    def _extract_currency(self, soup: BeautifulSoup) -> Optional[str]:
        currency_meta = soup.find("meta", property="product:price:currency")
        return currency_meta.get("content") if currency_meta else "USD"

    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        desc_meta = soup.find("meta", property="og:description")
        if desc_meta:
            return desc_meta.get("content")
        desc = soup.find("meta", attrs={"name": "description"})
        return desc.get("content") if desc else None

    def _extract_availability(self, soup: BeautifulSoup) -> str:
        availability_meta = soup.find("meta", property="product:availability")
        return availability_meta.get("content", "unknown") if availability_meta else "unknown"

    def _extract_rating(self, soup: BeautifulSoup) -> Optional[float]:
        rating_meta = soup.find("meta", property="product:rating")
        if rating_meta:
            try:
                return float(rating_meta.get("content", 0))
            except (ValueError, TypeError):
                pass
        return None

    def _extract_reviews_count(self, soup: BeautifulSoup) -> Optional[int]:
        reviews_meta = soup.find("meta", property="product:rating_count")
        if reviews_meta:
            try:
                return int(reviews_meta.get("content", 0))
            except (ValueError, TypeError):
                pass
        return None

    def _extract_specifications(self, soup: BeautifulSoup) -> Dict[str, str]:
        specs = {}
        spec_tables = soup.find_all("table", class_=lambda x: x and "spec" in x.lower())
        for table in spec_tables:
            for row in table.find_all("tr"):
                cells = row.find_all(["td", "th"])
                if len(cells) >= 2:
                    specs[cells[0].get_text(strip=True)] = cells[1].get_text(strip=True)
        return specs


web_scraper = WebScraper()
