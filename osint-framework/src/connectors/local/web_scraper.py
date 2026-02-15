"""
Web Scraper & Technology Fingerprinter — No API Keys Required

Scrapes websites via direct HTTP requests, extracts metadata, emails,
social links, and detects technologies from HTML/headers.
"""

import asyncio
import re
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# Technology signatures: (category, name, detection_patterns)
TECH_SIGNATURES = {
    # CMS
    "WordPress": {"headers": [], "html": ['wp-content', 'wp-includes', 'wordpress'], "meta": {"generator": "wordpress"}, "cookies": ["wordpress_"]},
    "Drupal": {"headers": ["X-Drupal-Cache"], "html": ['drupal.js', 'Drupal.settings', 'sites/default/files'], "meta": {"generator": "drupal"}, "cookies": []},
    "Joomla": {"headers": [], "html": ['/media/jui/', '/templates/joomla'], "meta": {"generator": "joomla"}, "cookies": []},
    "Wix": {"headers": ["X-Wix-Request-Id"], "html": ['wix.com', 'wixsite.com', '_wix_browser_sess'], "meta": {}, "cookies": []},
    "Squarespace": {"headers": [], "html": ['squarespace.com', 'static.squarespace.com'], "meta": {}, "cookies": ["SS_MID"]},
    "Shopify": {"headers": ["X-ShopId"], "html": ['cdn.shopify.com', 'Shopify.theme'], "meta": {}, "cookies": ["_shopify_"]},
    "Ghost": {"headers": ["X-Ghost-Cache-Status"], "html": ['ghost.org', 'ghost-url'], "meta": {"generator": "ghost"}, "cookies": []},
    # Frameworks
    "React": {"headers": [], "html": ['react.js', 'react-dom', '__NEXT_DATA__', '_next/static', 'reactroot'], "meta": {}, "cookies": []},
    "Next.js": {"headers": ["X-Nextjs-Page", "x-nextjs-cache"], "html": ['__NEXT_DATA__', '_next/'], "meta": {}, "cookies": []},
    "Vue.js": {"headers": [], "html": ['vue.js', 'vue.min.js', 'vue-router', '__vue__'], "meta": {}, "cookies": []},
    "Angular": {"headers": [], "html": ['ng-app', 'ng-version', 'angular.js', 'angular.min.js'], "meta": {}, "cookies": []},
    "Svelte": {"headers": [], "html": ['svelte', '__svelte'], "meta": {}, "cookies": []},
    "jQuery": {"headers": [], "html": ['jquery.js', 'jquery.min.js', 'jquery-'], "meta": {}, "cookies": []},
    "Bootstrap": {"headers": [], "html": ['bootstrap.css', 'bootstrap.min.css', 'bootstrap.js'], "meta": {}, "cookies": []},
    "Tailwind": {"headers": [], "html": ['tailwindcss', 'tailwind.min.css'], "meta": {}, "cookies": []},
    # Web servers
    "Nginx": {"headers": ["server:nginx"], "html": [], "meta": {}, "cookies": []},
    "Apache": {"headers": ["server:apache"], "html": [], "meta": {}, "cookies": []},
    "IIS": {"headers": ["server:microsoft-iis"], "html": [], "meta": {}, "cookies": ["ASP.NET_SessionId"]},
    "Cloudflare": {"headers": ["server:cloudflare", "cf-ray"], "html": [], "meta": {}, "cookies": ["__cfduid", "__cf_bm"]},
    "Vercel": {"headers": ["x-vercel-id", "server:vercel"], "html": [], "meta": {}, "cookies": []},
    "Netlify": {"headers": ["x-nf-request-id", "server:netlify"], "html": [], "meta": {}, "cookies": []},
    # Analytics & Tracking
    "Google Analytics": {"headers": [], "html": ['google-analytics.com', 'googletagmanager.com', 'gtag/js', 'ga.js', 'analytics.js'], "meta": {}, "cookies": ["_ga", "_gid"]},
    "Google Tag Manager": {"headers": [], "html": ['googletagmanager.com/gtm.js'], "meta": {}, "cookies": []},
    "Facebook Pixel": {"headers": [], "html": ['connect.facebook.net', 'fbevents.js', 'facebook.com/tr'], "meta": {}, "cookies": ["_fbp"]},
    "Hotjar": {"headers": [], "html": ['hotjar.com', 'static.hotjar.com'], "meta": {}, "cookies": ["_hj"]},
    # Security
    "reCAPTCHA": {"headers": [], "html": ['google.com/recaptcha', 'recaptcha/api.js'], "meta": {}, "cookies": []},
    "hCaptcha": {"headers": [], "html": ['hcaptcha.com', 'hcaptcha.js'], "meta": {}, "cookies": []},
    # CDN
    "AWS CloudFront": {"headers": ["x-amz-cf-id", "x-amz-cf-pop"], "html": [], "meta": {}, "cookies": []},
    "Akamai": {"headers": ["x-akamai-transformed"], "html": [], "meta": {}, "cookies": []},
    "Fastly": {"headers": ["x-served-by", "x-fastly-request-id"], "html": [], "meta": {}, "cookies": []},
    # Ecommerce
    "WooCommerce": {"headers": [], "html": ['woocommerce', 'wc-cart'], "meta": {}, "cookies": ["woocommerce_"]},
    "Magento": {"headers": [], "html": ['mage/', 'Magento_', 'magento'], "meta": {}, "cookies": ["mage-"]},
}


@dataclass
class WebPage:
    url: str
    status_code: int = 0
    title: str = ""
    description: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    technologies: List[str] = field(default_factory=list)
    emails: List[str] = field(default_factory=list)
    phones: List[str] = field(default_factory=list)
    social_links: Dict[str, str] = field(default_factory=dict)
    external_links: List[str] = field(default_factory=list)
    scripts: List[str] = field(default_factory=list)
    meta_tags: Dict[str, str] = field(default_factory=dict)
    security_headers: Dict[str, Any] = field(default_factory=dict)
    open_graph: Dict[str, str] = field(default_factory=dict)
    robots_txt: Optional[str] = None
    sitemap_urls: List[str] = field(default_factory=list)
    favicon_url: Optional[str] = None
    language: Optional[str] = None
    generator: Optional[str] = None
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v}


class WebScraper:
    """Web intelligence via direct HTTP requests + HTML parsing."""

    def __init__(self, timeout: float = 15.0, max_redirects: int = 5):
        self.timeout = timeout
        self.max_redirects = max_redirects
        self.logger = logging.getLogger(f"{__name__}.WebScraper")

    async def analyze(self, url: str, progress_callback=None) -> WebPage:
        """Full web analysis: fetch page, extract metadata, detect technologies."""
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        page = WebPage(url=url)

        try:
            if progress_callback:
                progress_callback("Web: Fetching page", 10)

            async with aiohttp.ClientSession() as session:
                headers = {
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                }
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=self.timeout),
                                       headers=headers, max_redirects=self.max_redirects,
                                       ssl=False) as resp:
                    page.status_code = resp.status
                    page.headers = {k.lower(): v for k, v in resp.headers.items()}
                    html = await resp.text(errors="replace")

                # Parse HTML
                if progress_callback:
                    progress_callback("Web: Analyzing content", 40)

                soup = BeautifulSoup(html, "html.parser")
                self._extract_metadata(soup, page, url)
                self._extract_emails(html, page)
                self._extract_phones(html, page)
                self._extract_social_links(soup, page, url)
                self._extract_scripts(soup, page, url)
                self._extract_open_graph(soup, page)

                if progress_callback:
                    progress_callback("Web: Detecting technologies", 60)

                self._detect_technologies(html, page, resp)

                if progress_callback:
                    progress_callback("Web: Checking security headers", 75)

                self._analyze_security_headers(page)

                # Fetch robots.txt
                if progress_callback:
                    progress_callback("Web: Fetching robots.txt", 85)

                await self._fetch_robots(session, url, page)

        except Exception as e:
            page.errors.append(f"Web analysis failed: {str(e)}")
            self.logger.warning(f"Web analysis failed for {url}: {e}")

        if progress_callback:
            progress_callback("Web: Complete", 100)

        return page

    def _extract_metadata(self, soup: BeautifulSoup, page: WebPage, base_url: str):
        # Title
        title_tag = soup.find("title")
        if title_tag:
            page.title = title_tag.get_text(strip=True)

        # Meta tags
        for meta in soup.find_all("meta"):
            name = meta.get("name", meta.get("property", "")).lower()
            content = meta.get("content", "")
            if name and content:
                page.meta_tags[name] = content
                if name == "description":
                    page.description = content
                elif name == "generator":
                    page.generator = content

        # Language
        html_tag = soup.find("html")
        if html_tag:
            page.language = html_tag.get("lang", "")

        # Favicon
        favicon = soup.find("link", rel=lambda x: x and "icon" in x.lower() if isinstance(x, str)
                            else any("icon" in r.lower() for r in x) if x else False)
        if favicon and favicon.get("href"):
            page.favicon_url = urljoin(base_url, favicon["href"])

    def _extract_emails(self, html: str, page: WebPage):
        emails = set()
        # Standard email pattern
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        for match in re.finditer(pattern, html):
            email = match.group().lower()
            # Filter out common false positives
            if not any(email.endswith(ext) for ext in ['.png', '.jpg', '.gif', '.css', '.js', '.svg', '.woff']):
                emails.add(email)
        page.emails = sorted(emails)

    def _extract_phones(self, html: str, page: WebPage):
        phones = set()
        patterns = [
            r'\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',
            r'tel:([+\d\-\s().]+)',
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, html):
                phone = match.group().strip()
                digits = re.sub(r'\D', '', phone)
                if 7 <= len(digits) <= 15:
                    phones.add(phone)
        page.phones = sorted(phones)[:20]  # Cap at 20

    def _extract_social_links(self, soup: BeautifulSoup, page: WebPage, base_url: str):
        social_patterns = {
            "twitter": [r"twitter\.com/", r"x\.com/"],
            "facebook": [r"facebook\.com/"],
            "instagram": [r"instagram\.com/"],
            "linkedin": [r"linkedin\.com/"],
            "youtube": [r"youtube\.com/", r"youtu\.be/"],
            "github": [r"github\.com/"],
            "tiktok": [r"tiktok\.com/"],
            "reddit": [r"reddit\.com/"],
            "discord": [r"discord\.gg/", r"discord\.com/"],
            "telegram": [r"t\.me/"],
            "mastodon": [r"mastodon\.", r"fosstodon\.org", r"hachyderm\.io"],
            "bluesky": [r"bsky\.app/"],
            "pinterest": [r"pinterest\.com/"],
            "medium": [r"medium\.com/"],
        }
        for link in soup.find_all("a", href=True):
            href = link["href"].lower()
            for platform, patterns in social_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, href):
                        page.social_links[platform] = link["href"]
                        break

    def _extract_scripts(self, soup: BeautifulSoup, page: WebPage, base_url: str):
        for script in soup.find_all("script", src=True):
            src = script["src"]
            full_url = urljoin(base_url, src)
            page.scripts.append(full_url)

    def _extract_open_graph(self, soup: BeautifulSoup, page: WebPage):
        for meta in soup.find_all("meta", property=lambda x: x and x.startswith("og:")):
            prop = meta["property"][3:]  # Remove "og:"
            content = meta.get("content", "")
            if content:
                page.open_graph[prop] = content

    def _detect_technologies(self, html: str, page: WebPage, response=None):
        html_lower = html.lower()
        headers_lower = {k.lower(): v.lower() for k, v in page.headers.items()}

        detected = set()
        for tech_name, signatures in TECH_SIGNATURES.items():
            found = False

            # Check headers
            for header_sig in signatures.get("headers", []):
                if ":" in header_sig:
                    h_name, h_val = header_sig.lower().split(":", 1)
                    if h_name in headers_lower and h_val in headers_lower[h_name]:
                        found = True
                        break
                else:
                    if header_sig.lower() in headers_lower:
                        found = True
                        break

            # Check HTML content
            if not found:
                for pattern in signatures.get("html", []):
                    if pattern.lower() in html_lower:
                        found = True
                        break

            # Check meta tags
            if not found:
                for meta_name, meta_val in signatures.get("meta", {}).items():
                    page_meta = page.meta_tags.get(meta_name, "").lower()
                    if meta_val.lower() in page_meta:
                        found = True
                        break

            if found:
                detected.add(tech_name)

        page.technologies = sorted(detected)

    def _analyze_security_headers(self, page: WebPage):
        security_checks = {
            "strict-transport-security": {"present": False, "value": None, "rating": "missing"},
            "content-security-policy": {"present": False, "value": None, "rating": "missing"},
            "x-frame-options": {"present": False, "value": None, "rating": "missing"},
            "x-content-type-options": {"present": False, "value": None, "rating": "missing"},
            "x-xss-protection": {"present": False, "value": None, "rating": "missing"},
            "referrer-policy": {"present": False, "value": None, "rating": "missing"},
            "permissions-policy": {"present": False, "value": None, "rating": "missing"},
        }

        for header, info in security_checks.items():
            if header in page.headers:
                info["present"] = True
                info["value"] = page.headers[header]
                info["rating"] = "good"

        # Score
        present_count = sum(1 for v in security_checks.values() if v["present"])
        score = int((present_count / len(security_checks)) * 100)
        page.security_headers = {
            "score": score,
            "grade": "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 50 else "D" if score >= 30 else "F",
            "checks": security_checks,
        }

    async def _fetch_robots(self, session: aiohttp.ClientSession, url: str, page: WebPage):
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        try:
            async with session.get(robots_url, timeout=aiohttp.ClientTimeout(total=5), ssl=False) as resp:
                if resp.status == 200:
                    page.robots_txt = await resp.text(errors="replace")
                    # Extract sitemaps
                    for line in page.robots_txt.split("\n"):
                        if line.lower().startswith("sitemap:"):
                            page.sitemap_urls.append(line.split(":", 1)[1].strip())
        except Exception:
            pass
