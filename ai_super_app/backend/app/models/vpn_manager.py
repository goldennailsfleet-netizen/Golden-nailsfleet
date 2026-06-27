"""
VPN Manager - Smart proxy rotation and web access
"""
import asyncio
import random
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import httpx
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup


@dataclass
class ProxyServer:
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: str = "http"
    country: str = "US"
    latency_ms: float = 0.0
    success_rate: float = 1.0
    last_used: float = 0.0
    failure_count: int = 0
    is_active: bool = True

    @property
    def url(self) -> str:
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"


class VPNManager:
    def __init__(self):
        self.proxies: List[ProxyServer] = []
        self.current_proxy_index: int = 0
        self.request_count: int = 0
        self.failed_proxies: set = set()
        self._init_proxies()

    def _init_proxies(self):
        from app.config import settings
        if settings.PROXY_LIST:
            for proxy_url in settings.PROXY_LIST:
                self._parse_proxy_url(proxy_url)
        else:
            self.proxies = [
                ProxyServer(host="us-proxy1.example.com", port=8080, country="US"),
                ProxyServer(host="eu-proxy1.example.com", port=8080, country="EU"),
                ProxyServer(host="asia-proxy1.example.com", port=8080, country="JP"),
            ]

    def _parse_proxy_url(self, url: str):
        pass

    def get_proxy(self, prefer_country: Optional[str] = None) -> Optional[ProxyServer]:
        available = [p for p in self.proxies if p.is_active and p not in self.failed_proxies]
        if not available:
            self.failed_proxies.clear()
            available = self.proxies

        if prefer_country:
            country_proxies = [p for p in available if p.country == prefer_country]
            if country_proxies:
                available = country_proxies

        weights = []
        for proxy in available:
            weight = proxy.success_rate * 100
            weight += (1000 - min(proxy.latency_ms, 1000)) / 10
            time_since_used = time.time() - proxy.last_used
            weight += min(time_since_used, 60) / 6
            weights.append(max(weight, 1))

        selected = random.choices(available, weights=weights, k=1)[0]
        selected.last_used = time.time()
        self.request_count += 1
        return selected

    def report_failure(self, proxy: ProxyServer):
        proxy.failure_count += 1
        proxy.success_rate = max(0.1, proxy.success_rate - 0.1)
        if proxy.failure_count >= 3:
            self.failed_proxies.add(proxy)
            proxy.is_active = False

    def report_success(self, proxy: ProxyServer):
        proxy.success_rate = min(1.0, proxy.success_rate + 0.05)
        proxy.failure_count = max(0, proxy.failure_count - 1)

    async def fetch_url(self, url: str, headers: Optional[Dict] = None,
                       prefer_country: Optional[str] = None,
                       use_js: bool = False) -> Dict[str, Any]:
        proxy = self.get_proxy(prefer_country)
        if not proxy:
            return {"success": False, "error": "No available proxies"}

        start_time = time.time()
        try:
            if use_js:
                result = await self._fetch_with_playwright(url, proxy, headers)
            else:
                result = await self._fetch_with_httpx(url, proxy, headers)

            latency = (time.time() - start_time) * 1000
            proxy.latency_ms = latency
            self.report_success(proxy)

            return {
                "success": True, "content": result,
                "proxy_used": f"{proxy.country}-{proxy.host}",
                "latency_ms": latency
            }
        except Exception:
            self.report_failure(proxy)
            return await self.fetch_url(url, headers, prefer_country, use_js)

    async def _fetch_with_httpx(self, url: str, proxy: ProxyServer,
                                headers: Optional[Dict]) -> str:
        async with httpx.AsyncClient(
            proxies={"http://": proxy.url, "https://": proxy.url},
            timeout=30.0, follow_redirects=True
        ) as client:
            response = await client.get(url, headers=headers or self._default_headers())
            response.raise_for_status()
            return response.text

    async def _fetch_with_playwright(self, url: str, proxy: ProxyServer,
                                     headers: Optional[Dict]) -> str:
        async with async_playwright() as p:
            browser = await p.chromium.launch(proxy={"server": proxy.url} if proxy else None)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            await page.goto(url, wait_until="networkidle")
            content = await page.content()
            await browser.close()
            return content

    def _default_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1", "Connection": "keep-alive",
        }

    async def scrape_website(self, url: str, extract_text: bool = True,
                            extract_images: bool = False,
                            extract_links: bool = False) -> Dict[str, Any]:
        result = await self.fetch_url(url, use_js=True)
        if not result.get("success", True):
            return result

        content = result["content"]
        soup = BeautifulSoup(content, "html.parser")

        extracted_data = {
            "url": url, "proxy_used": result.get("proxy_used"),
            "latency_ms": result.get("latency_ms"),
            "title": soup.title.string if soup.title else None,
        }

        if extract_text:
            for script in soup(["script", "style"]):
                script.decompose()
            text = soup.get_text(separator="\n", strip=True)
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            extracted_data["text_content"] = "\n".join(lines)
            extracted_data["text_length"] = len(extracted_data["text_content"])

        if extract_images:
            images = []
            for img in soup.find_all("img"):
                src = img.get("src", "")
                if src.startswith("http"):
                    images.append({
                        "src": src, "alt": img.get("alt", ""),
                        "width": img.get("width"), "height": img.get("height")
                    })
            extracted_data["images"] = images
            extracted_data["image_count"] = len(images)

        if extract_links:
            links = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if href.startswith("http"):
                    links.append({"url": href, "text": a.get_text(strip=True),
                                  "title": a.get("title", "")})
            extracted_data["links"] = links
            extracted_data["link_count"] = len(links)

        return extracted_data


vpn_manager = VPNManager()
