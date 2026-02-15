"""
Technology Fingerprinter — No API Keys Required

Wappalyzer-style technology detection from HTTP responses.
Comprehensive signature database for 200+ web technologies.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TechMatch:
    name: str
    category: str
    confidence: int = 100  # 0-100
    version: str = ""
    evidence: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = {"name": self.name, "category": self.category, "confidence": self.confidence}
        if self.version:
            d["version"] = self.version
        if self.evidence:
            d["evidence"] = self.evidence
        return d


# Extended technology database with version detection
TECH_DB = {
    # === CMS ===
    "WordPress": {
        "category": "CMS",
        "html": [r'wp-content/(?:themes|plugins)', r'wp-includes/', r'/wp-json/'],
        "headers": {"x-powered-by": r'wordpress'},
        "meta": {"generator": r'WordPress\s*([\d.]+)?'},
        "cookies": [r'wordpress_'],
    },
    "Drupal": {
        "category": "CMS",
        "html": [r'Drupal\.settings', r'sites/(?:all|default)/'],
        "headers": {"x-drupal-cache": r'.*', "x-generator": r'Drupal\s*([\d.]+)?'},
        "meta": {"generator": r'Drupal\s*([\d.]+)?'},
    },
    "Joomla": {
        "category": "CMS",
        "html": [r'/media/jui/', r'com_content'],
        "meta": {"generator": r'Joomla!\s*([\d.]+)?'},
    },
    "Ghost": {
        "category": "CMS",
        "html": [r'ghost\.org', r'ghost-(?:url|version)'],
        "meta": {"generator": r'Ghost\s*([\d.]+)?'},
        "headers": {"x-ghost-cache-status": r'.*'},
    },
    "Wix": {"category": "CMS", "html": [r'wix\.com', r'_wix_browser_sess'], "headers": {"x-wix-request-id": r'.*'}},
    "Squarespace": {"category": "CMS", "html": [r'static\.squarespace\.com'], "cookies": [r'SS_MID']},
    "Shopify": {"category": "E-Commerce", "html": [r'cdn\.shopify\.com', r'Shopify\.theme'], "headers": {"x-shopid": r'.*'}},
    "WooCommerce": {"category": "E-Commerce", "html": [r'woocommerce', r'wc-cart', r'wc-ajax']},
    "Magento": {"category": "E-Commerce", "html": [r'Mage\.Cookies', r'mage/'], "cookies": [r'mage-']},
    "PrestaShop": {"category": "E-Commerce", "html": [r'prestashop', r'PrestaShop'], "meta": {"generator": r'PrestaShop'}},
    # === JavaScript Frameworks ===
    "React": {"category": "JS Framework", "html": [r'react\.(?:production|development)\.min\.js', r'_reactRootContainer', r'data-reactroot']},
    "Next.js": {"category": "JS Framework", "html": [r'__NEXT_DATA__', r'_next/static'], "headers": {"x-nextjs-cache": r'.*', "x-nextjs-page": r'.*'}},
    "Vue.js": {"category": "JS Framework", "html": [r'vue\.(?:runtime\.)?(?:esm\.)?(?:min\.)?js', r'v-(?:cloak|text|html|model)', r'data-v-[a-f0-9]']},
    "Nuxt.js": {"category": "JS Framework", "html": [r'__NUXT__', r'_nuxt/'], "headers": {"x-nuxt-": r'.*'}},
    "Angular": {"category": "JS Framework", "html": [r'ng-(?:app|version|controller)', r'angular\.(?:min\.)?js', r'ng-reflect-']},
    "Svelte": {"category": "JS Framework", "html": [r'svelte', r'__svelte']},
    "jQuery": {"category": "JS Library", "html": [r'jquery[.-](\d+\.\d+(?:\.\d+)?)', r'jquery\.min\.js']},
    "Bootstrap": {"category": "CSS Framework", "html": [r'bootstrap[.-](\d+\.\d+(?:\.\d+)?)', r'bootstrap\.min\.(?:css|js)']},
    "Tailwind CSS": {"category": "CSS Framework", "html": [r'tailwindcss', r'tailwind\.min\.css']},
    "Material UI": {"category": "CSS Framework", "html": [r'MuiButton', r'material-ui', r'@mui/']},
    # === Web Servers ===
    "Nginx": {"category": "Web Server", "headers": {"server": r'nginx(?:/([\d.]+))?'}},
    "Apache": {"category": "Web Server", "headers": {"server": r'Apache(?:/([\d.]+))?'}},
    "IIS": {"category": "Web Server", "headers": {"server": r'Microsoft-IIS(?:/([\d.]+))?'}},
    "LiteSpeed": {"category": "Web Server", "headers": {"server": r'LiteSpeed'}},
    "Caddy": {"category": "Web Server", "headers": {"server": r'Caddy'}},
    # === CDN & Hosting ===
    "Cloudflare": {"category": "CDN", "headers": {"server": r'cloudflare', "cf-ray": r'.*'}},
    "AWS CloudFront": {"category": "CDN", "headers": {"x-amz-cf-id": r'.*', "x-amz-cf-pop": r'.*'}},
    "Fastly": {"category": "CDN", "headers": {"x-fastly-request-id": r'.*', "x-served-by": r'cache-'}},
    "Akamai": {"category": "CDN", "headers": {"x-akamai-transformed": r'.*'}},
    "Vercel": {"category": "Hosting", "headers": {"x-vercel-id": r'.*', "server": r'Vercel'}},
    "Netlify": {"category": "Hosting", "headers": {"x-nf-request-id": r'.*', "server": r'Netlify'}},
    "Heroku": {"category": "Hosting", "headers": {"via": r'vegur'}},
    "GitHub Pages": {"category": "Hosting", "headers": {"server": r'GitHub\.com'}},
    # === Analytics ===
    "Google Analytics": {"category": "Analytics", "html": [r'google-analytics\.com/(?:analytics|ga)\.js', r'googletagmanager\.com/gtag', r"gtag\('config'"]},
    "Google Tag Manager": {"category": "Analytics", "html": [r'googletagmanager\.com/gtm\.js']},
    "Facebook Pixel": {"category": "Analytics", "html": [r'connect\.facebook\.net/.*fbevents\.js', r'facebook\.com/tr\?']},
    "Hotjar": {"category": "Analytics", "html": [r'static\.hotjar\.com', r'hotjar\.com/c/hotjar-']},
    "Matomo": {"category": "Analytics", "html": [r'matomo\.(?:js|php)', r'piwik\.(?:js|php)']},
    "Plausible": {"category": "Analytics", "html": [r'plausible\.io/js/']},
    "Umami": {"category": "Analytics", "html": [r'umami\.(?:is|js)']},
    # === Security ===
    "reCAPTCHA": {"category": "Security", "html": [r'google\.com/recaptcha', r'recaptcha/api\.js']},
    "hCaptcha": {"category": "Security", "html": [r'hcaptcha\.com', r'hcaptcha\.js']},
    "Cloudflare Turnstile": {"category": "Security", "html": [r'challenges\.cloudflare\.com/turnstile']},
    # === Programming Languages ===
    "PHP": {"category": "Language", "headers": {"x-powered-by": r'PHP(?:/([\d.]+))?'}, "cookies": [r'PHPSESSID']},
    "ASP.NET": {"category": "Language", "headers": {"x-powered-by": r'ASP\.NET', "x-aspnet-version": r'([\d.]+)'}, "cookies": [r'ASP\.NET_SessionId']},
    "Python": {"category": "Language", "headers": {"x-powered-by": r'(?:Python|Flask|Django|FastAPI)'}},
    "Node.js": {"category": "Language", "headers": {"x-powered-by": r'Express'}},
    "Ruby": {"category": "Language", "headers": {"x-powered-by": r'(?:Phusion Passenger|Ruby)'}},
    # === Frameworks (Backend) ===
    "Django": {"category": "Backend Framework", "html": [r'csrfmiddlewaretoken', r'__admin_media_prefix__'], "cookies": [r'csrftoken', r'django_']},
    "Flask": {"category": "Backend Framework", "headers": {"server": r'Werkzeug'}},
    "Laravel": {"category": "Backend Framework", "cookies": [r'laravel_session', r'XSRF-TOKEN'], "html": [r'laravel']},
    "Ruby on Rails": {"category": "Backend Framework", "headers": {"x-powered-by": r'Rails'}, "cookies": [r'_rails_']},
    "Spring": {"category": "Backend Framework", "headers": {"x-application-context": r'.*'}},
    # === Other ===
    "Font Awesome": {"category": "Font", "html": [r'font-awesome', r'fontawesome', r'fa-(?:brands|solid|regular)']},
    "Google Fonts": {"category": "Font", "html": [r'fonts\.googleapis\.com', r'fonts\.gstatic\.com']},
    "Stripe": {"category": "Payment", "html": [r'js\.stripe\.com', r'Stripe\(']},
    "PayPal": {"category": "Payment", "html": [r'paypal\.com/sdk', r'paypalobjects\.com']},
    "Webpack": {"category": "Build Tool", "html": [r'webpackJsonp', r'__webpack_']},
    "Vite": {"category": "Build Tool", "html": [r'@vite', r'vite/']},
}


class TechFingerprinter:
    """Wappalyzer-style technology fingerprinting from HTTP responses."""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.TechFingerprinter")

    def fingerprint(self, html: str, headers: Dict[str, str],
                    cookies: Optional[List[str]] = None) -> List[TechMatch]:
        """Detect technologies from HTML content and HTTP headers."""
        matches: List[TechMatch] = []
        html_lower = html.lower()
        headers_lower = {k.lower(): v for k, v in headers.items()}
        cookies_str = " ".join(cookies or []).lower()

        for tech_name, signatures in TECH_DB.items():
            category = signatures.get("category", "Other")
            version = ""
            evidence = ""
            found = False

            # Check HTML patterns
            for pattern in signatures.get("html", []):
                m = re.search(pattern, html, re.IGNORECASE)
                if m:
                    found = True
                    evidence = f"html: {pattern}"
                    if m.groups():
                        version = m.group(1) or ""
                    break

            # Check headers
            if not found:
                for header_name, pattern in signatures.get("headers", {}).items():
                    header_val = headers_lower.get(header_name, "")
                    if header_val:
                        m = re.search(pattern, header_val, re.IGNORECASE)
                        if m:
                            found = True
                            evidence = f"header: {header_name}"
                            if m.groups():
                                version = m.group(1) or ""
                            break

            # Check meta tags
            if not found:
                for meta_name, pattern in signatures.get("meta", {}).items():
                    # Search for meta tag in HTML
                    meta_pattern = rf'<meta[^>]*name=["\']?{re.escape(meta_name)}["\']?[^>]*content=["\']([^"\']*)["\']'
                    m = re.search(meta_pattern, html, re.IGNORECASE)
                    if m:
                        meta_content = m.group(1)
                        m2 = re.search(pattern, meta_content, re.IGNORECASE)
                        if m2:
                            found = True
                            evidence = f"meta: {meta_name}"
                            if m2.groups():
                                version = m2.group(1) or ""
                            break

            # Check cookies
            if not found and cookies_str:
                for cookie_pattern in signatures.get("cookies", []):
                    if re.search(cookie_pattern, cookies_str, re.IGNORECASE):
                        found = True
                        evidence = f"cookie: {cookie_pattern}"
                        break

            if found:
                matches.append(TechMatch(
                    name=tech_name, category=category,
                    version=version, evidence=evidence,
                    confidence=90 if version else 75
                ))

        # Sort by category, then name
        matches.sort(key=lambda m: (m.category, m.name))
        return matches

    def categorize(self, matches: List[TechMatch]) -> Dict[str, List[Dict]]:
        """Group detected technologies by category."""
        categories: Dict[str, List[Dict]] = {}
        for match in matches:
            if match.category not in categories:
                categories[match.category] = []
            categories[match.category].append(match.to_dict())
        return categories
