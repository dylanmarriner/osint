"""
Person Reconnaissance Module — Advanced OSINT Search by Name, DOB, Location

Uses techniques that ACTUALLY produce results without API keys:
  1. Direct social profile URL probing (Sherlock-style HEAD/GET requests)
  2. Username enumeration across 60+ platforms
  3. Google/Bing dorking via HTML scraping
  4. GitHub API deep user info (no key needed for basic)
  5. Gravatar hash check
  6. HaveIBeenPwned-style breach directory lookup
  7. Email permutation + MX validation
  8. People-finder site scraping with anti-bot bypass
  9. Wayback Machine CDX API
  10. DNS-based data enrichment
"""

import asyncio
import aiohttp
import hashlib
import logging
import random
import re
import json
import ssl
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import quote_plus, quote
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class PersonReport:
    """Results of a person investigation."""
    full_name: str = ""
    first_name: str = ""
    last_name: str = ""
    middle_name: str = ""
    date_of_birth: str = ""
    age: int = 0
    location: str = ""
    city: str = ""
    state: str = ""
    country: str = ""

    # Discovered data
    possible_emails: List[str] = field(default_factory=list)
    possible_usernames: List[str] = field(default_factory=list)
    social_profiles: List[Dict[str, Any]] = field(default_factory=list)
    web_mentions: List[Dict[str, Any]] = field(default_factory=list)
    archived_pages: List[Dict[str, Any]] = field(default_factory=list)
    public_records: List[Dict[str, Any]] = field(default_factory=list)
    phone_numbers: List[str] = field(default_factory=list)
    addresses: List[str] = field(default_factory=list)
    relatives: List[str] = field(default_factory=list)
    employers: List[str] = field(default_factory=list)
    education: List[str] = field(default_factory=list)
    breaches: List[Dict[str, Any]] = field(default_factory=list)
    gravatar: Dict[str, Any] = field(default_factory=dict)
    github_details: List[Dict[str, Any]] = field(default_factory=list)
    documents: List[Dict[str, Any]] = field(default_factory=list)

    # Analysis
    confidence_score: float = 0.0
    data_sources: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v}


# ==================== Anti-Detection Stealth Layer ====================

# Full browser fingerprint sets — each contains a matched UA + headers that
# real browsers actually send together.  Mixing UA from Chrome with headers
# from Firefox is a dead giveaway; we avoid that entirely.

_BROWSER_FINGERPRINTS = [
    # Chrome 122 on Windows 10
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
    },
    # Chrome 121 on macOS
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-Ch-Ua": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    },
    # Firefox 123 on Linux
    {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Connection": "keep-alive",
    },
    # Firefox 122 on Windows
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    },
    # Safari 17.2 on macOS
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
    },
    # Edge 121 on Windows
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-Ch-Ua": '"Not A(Brand";v="99", "Microsoft Edge";v="121", "Chromium";v="121"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    },
    # Chrome 120 on Windows 11
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    },
    # Firefox 121 on macOS
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
    },
]

# Referer chains — appear to come from normal browsing
_REFERERS = [
    "https://www.google.com/",
    "https://www.google.com/search?q=",
    "https://www.bing.com/search?q=",
    "https://duckduckgo.com/",
    "https://search.yahoo.com/",
    "",  # Direct navigation (no referer)
]


def _stealth_ssl_context() -> ssl.SSLContext:
    """Create an SSL context that mimics a real browser's TLS fingerprint."""
    ctx = ssl.create_default_context()
    # Browsers negotiate modern cipher suites; we mirror that
    ctx.set_ciphers(
        "ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS"
    )
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _random_delay(base: float = 0.3, jitter: float = 0.7) -> float:
    """Generate a human-like random delay to avoid timing fingerprinting."""
    return base + random.random() * jitter


class StealthSession:
    """
    A wrapper around aiohttp.ClientSession that mimics real browser behaviour:
    - Picks a random browser fingerprint and uses it consistently per session
    - Rotates referers to simulate organic browsing
    - Adds random delays between requests
    - Maintains a cookie jar across requests
    - Uses a realistic TLS configuration
    """

    def __init__(self):
        self._fingerprint = random.choice(_BROWSER_FINGERPRINTS)
        self._cookie_jar = aiohttp.CookieJar(unsafe=True)
        self._ssl_ctx = _stealth_ssl_context()
        self._session: Optional[aiohttp.ClientSession] = None
        self._request_count = 0

    async def __aenter__(self):
        self._session = aiohttp.ClientSession(
            headers=self._fingerprint.copy(),
            cookie_jar=self._cookie_jar,
            timeout=aiohttp.ClientTimeout(total=12, connect=8),
            connector=aiohttp.TCPConnector(
                limit=15,
                ssl=self._ssl_ctx,
                enable_cleanup_closed=True,
            ),
        )
        return self

    async def __aexit__(self, *args):
        if self._session:
            await self._session.close()

    async def get(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        """GET with automatic stealth headers and pacing."""
        # Organic delay between requests
        if self._request_count > 0:
            await asyncio.sleep(_random_delay(0.15, 0.5))
        self._request_count += 1

        # Rotate referer occasionally
        headers = kwargs.pop("headers", {})
        if "Referer" not in headers and random.random() > 0.3:
            headers["Referer"] = random.choice(_REFERERS)

        return await self._session.get(url, headers=headers, allow_redirects=True, **kwargs)

    async def get_text(self, url: str, **kwargs) -> tuple:
        """GET and return (status, text) — convenience method."""
        try:
            resp = await self.get(url, **kwargs)
            text = await resp.text()
            return resp.status, text
        except Exception:
            return 0, ""

    @property
    def session(self) -> aiohttp.ClientSession:
        return self._session


class PersonRecon:
    """
    Person reconnaissance engine — uses techniques that actually work.
    No API keys required. All sources are free and publicly accessible.
    Anti-detection: realistic browser fingerprints, random delays, cookie
    persistence, proper TLS, and organic-looking request patterns.
    """

    EMAIL_DOMAINS = [
        "gmail.com", "yahoo.com", "outlook.com", "hotmail.com",
        "protonmail.com", "icloud.com", "aol.com", "mail.com",
        "live.com", "yandex.com",
    ]

    # Direct social profile URL patterns — check if profile EXISTS by HTTP status
    # {username} placeholder is replaced with each generated username
    SOCIAL_PROFILE_URLS = {
        "GitHub":         "https://github.com/{username}",
        "Twitter/X":      "https://x.com/{username}",
        "Instagram":      "https://www.instagram.com/{username}/",
        "Reddit":         "https://www.reddit.com/user/{username}",
        "Pinterest":      "https://www.pinterest.com/{username}/",
        "Medium":         "https://medium.com/@{username}",
        "Dev.to":         "https://dev.to/{username}",
        "Keybase":        "https://keybase.io/{username}",
        "HackerNews":     "https://news.ycombinator.com/user?id={username}",
        "Steam":          "https://steamcommunity.com/id/{username}",
        "Twitch":         "https://www.twitch.tv/{username}",
        "SoundCloud":     "https://soundcloud.com/{username}",
        "Bandcamp":       "https://{username}.bandcamp.com",
        "Spotify":        "https://open.spotify.com/user/{username}",
        "Flickr":         "https://www.flickr.com/people/{username}/",
        "Vimeo":          "https://vimeo.com/{username}",
        "Behance":        "https://www.behance.net/{username}",
        "Dribbble":       "https://dribbble.com/{username}",
        "GitLab":         "https://gitlab.com/{username}",
        "Bitbucket":      "https://bitbucket.org/{username}/",
        "npm":            "https://www.npmjs.com/~{username}",
        "PyPI":           "https://pypi.org/user/{username}/",
        "StackOverflow":  "https://stackoverflow.com/users/?tab=Reputation&filter=all&search={username}",
        "Replit":         "https://replit.com/@{username}",
        "CodePen":        "https://codepen.io/{username}",
        "Mastodon.social":"https://mastodon.social/@{username}",
        "Telegram":       "https://t.me/{username}",
        "TikTok":         "https://www.tiktok.com/@{username}",
        "YouTube":        "https://www.youtube.com/@{username}",
        "Tumblr":         "https://{username}.tumblr.com",
        "WordPress":      "https://{username}.wordpress.com",
        "Blogger":        "https://{username}.blogspot.com",
        "About.me":       "https://about.me/{username}",
        "Linktree":       "https://linktr.ee/{username}",
        "Cash App":       "https://cash.app/${username}",
        "Patreon":        "https://www.patreon.com/{username}",
        "Gist":           "https://gist.github.com/{username}",
        "Scribd":         "https://www.scribd.com/{username}",
        "SlideShare":     "https://www.slideshare.net/{username}",
        "Gravatar":       "https://en.gravatar.com/{username}",
        "Roblox":         "https://www.roblox.com/user.aspx?username={username}",
        "Minecraft":      "https://namemc.com/profile/{username}",
        "Chess.com":      "https://www.chess.com/member/{username}",
        "Lichess":        "https://lichess.org/@/{username}",
        "Hugging Face":   "https://huggingface.co/{username}",
        "Kaggle":         "https://www.kaggle.com/{username}",
        "Wikipedia":      "https://en.wikipedia.org/wiki/User:{username}",
        "Wikidata":       "https://www.wikidata.org/wiki/User:{username}",
        "Last.fm":        "https://www.last.fm/user/{username}",
        "Snapchat":       "https://www.snapchat.com/add/{username}",
    }

    # Platforms with known anti-bot that need special handling
    SEARCH_ONLY_PLATFORMS = {
        "LinkedIn":  "https://www.linkedin.com/in/{username}",
        "Facebook":  "https://www.facebook.com/{username}",
    }

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.PersonRecon")

    async def search(self, full_name: str, date_of_birth: str = "",
                     location: str = "", progress_callback: Optional[Callable] = None) -> PersonReport:
        """
        Run a comprehensive person search.

        Args:
            full_name: Full name (e.g. "John Michael Smith")
            date_of_birth: DOB in any format (e.g. "1990-01-15", "15/01/1990")
            location: City, state, country (e.g. "Auckland, New Zealand")
            progress_callback: Called with (message, percent)
        """
        report = PersonReport(full_name=full_name)
        self._parse_name(full_name, report)
        self._parse_dob(date_of_birth, report)
        self._parse_location(location, report)

        async def _progress(msg, pct):
            if progress_callback:
                progress_callback(f"Person Search: {msg}", pct)

        steps = [
            ("Generating usernames & emails",    5,  self._generate_usernames_and_emails),
            ("Probing social profiles",         15,  self._probe_social_profiles),
            ("Deep GitHub search",              35,  self._search_github_deep),
            ("Checking Gravatar",               40,  self._check_gravatar),
            ("Dorking: Google & Bing",          45,  self._search_engine_dork),
            ("Searching people databases",      60,  self._search_people_sites),
            ("Querying Wayback Machine",        70,  self._search_wayback),
            ("Checking breach directories",     78,  self._check_breaches),
            ("Validating emails",               85,  self._validate_emails),
            ("Computing confidence",            95,  self._calculate_confidence),
        ]

        for label, pct, func in steps:
            await _progress(label, pct)
            try:
                await func(report)
            except Exception as e:
                report.errors.append(f"{label}: {str(e)}")
                self.logger.warning(f"{label} failed: {e}")

        await _progress("Person search complete", 100)
        return report

    # ===== Name / DOB / Location Parsing =====

    def _parse_name(self, full_name: str, report: PersonReport):
        parts = full_name.strip().split()
        if len(parts) >= 1:
            report.first_name = parts[0].capitalize()
        if len(parts) >= 3:
            report.middle_name = " ".join(parts[1:-1]).capitalize()
            report.last_name = parts[-1].capitalize()
        elif len(parts) == 2:
            report.last_name = parts[1].capitalize()

    def _parse_dob(self, dob: str, report: PersonReport):
        if not dob:
            return
        report.date_of_birth = dob
        for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y",
                     "%d %B %Y", "%B %d, %Y", "%d %b %Y"]:
            try:
                dt = datetime.strptime(dob.strip(), fmt)
                today = datetime.now()
                report.age = today.year - dt.year - ((today.month, today.day) < (dt.month, dt.day))
                report.date_of_birth = dt.strftime("%Y-%m-%d")
                return
            except ValueError:
                continue

    def _parse_location(self, location: str, report: PersonReport):
        if not location:
            return
        report.location = location
        parts = [p.strip() for p in location.split(",")]
        if len(parts) >= 1:
            report.city = parts[0]
        if len(parts) >= 2:
            report.state = parts[1]
        if len(parts) >= 3:
            report.country = parts[2]

    # ===== Step 1: Username & Email Generation =====

    async def _generate_usernames_and_emails(self, report: PersonReport):
        first = report.first_name.lower()
        last = report.last_name.lower()
        if not first or not last:
            return

        # Year fragments
        year = year_short = ""
        if report.date_of_birth:
            try:
                dt = datetime.strptime(report.date_of_birth, "%Y-%m-%d")
                year = str(dt.year)
                year_short = str(dt.year)[-2:]
            except ValueError:
                pass

        mi = report.middle_name[0].lower() if report.middle_name else ""

        # Generate username variants
        patterns = [
            f"{first}{last}",       f"{first}.{last}",      f"{first}_{last}",
            f"{first}-{last}",      f"{first[0]}{last}",    f"{first}{last[0]}",
            f"{last}{first}",       f"{last}.{first}",      f"{last}_{first}",
        ]
        if year_short:
            patterns += [
                f"{first}{last}{year_short}", f"{first}.{last}{year_short}",
                f"{first}{year_short}",      f"{last}{year_short}",
                f"{first[0]}{last}{year_short}",
            ]
        if year:
            patterns += [f"{first}{last}{year}", f"{first}{year}"]
        if mi:
            patterns += [
                f"{first}{mi}{last}", f"{first}.{mi}.{last}", f"{first}_{mi}_{last}",
            ]

        report.possible_usernames = list(dict.fromkeys(patterns))  # Dedupe preserving order
        self.logger.info(f"Generated {len(report.possible_usernames)} usernames")

        # Generate email permutations
        local_parts = [
            f"{first}.{last}", f"{first}{last}", f"{first[0]}{last}",
            f"{first}_{last}", f"{last}.{first}", f"{first}{last[0]}",
        ]
        if mi:
            local_parts += [f"{first}.{mi}.{last}", f"{first}{mi}{last}"]
        if year_short:
            local_parts += [f"{first}.{last}{year_short}", f"{first}{last}{year_short}"]

        for domain in self.EMAIL_DOMAINS[:5]:
            for local in local_parts[:8]:
                report.possible_emails.append(f"{local}@{domain}")

        self.logger.info(f"Generated {len(report.possible_emails)} emails")

    # ===== Step 2: Direct Social Profile Probing (Sherlock-style) =====

    async def _probe_social_profiles(self, report: PersonReport):
        """Check if social profiles EXIST by probing direct URLs with stealth requests."""
        if not report.possible_usernames:
            return

        # Use top 5 most likely usernames
        top_usernames = report.possible_usernames[:5]

        async with StealthSession() as stealth:
            tasks = []
            # Shuffle platform order to avoid predictable request patterns
            platforms = list(self.SOCIAL_PROFILE_URLS.items())
            random.shuffle(platforms)

            for username in top_usernames:
                for platform, url_template in platforms:
                    url = url_template.replace("{username}", username)
                    tasks.append(self._probe_profile(stealth, platform, url, username, report))

            # Run in smaller batches with random pauses
            batch_size = 20
            for i in range(0, len(tasks), batch_size):
                batch = tasks[i:i + batch_size]
                await asyncio.gather(*batch, return_exceptions=True)
                await asyncio.sleep(_random_delay(0.4, 0.8))  # Human-like pause

    async def _probe_profile(self, stealth: StealthSession,
                              platform: str, url: str, username: str,
                              report: PersonReport):
        """Probe a single profile URL with stealth headers."""
        try:
            resp = await stealth.get(url)
            # Different platforms signal "found" differently
            if resp.status == 200:
                # Check if it's a real profile (not a 200 with "not found" message)
                content_length = resp.headers.get("Content-Length", "0")
                is_real = True

                # Some sites return 200 with "not found" content
                if int(content_length or 0) < 500 and platform not in ("Keybase", "About.me"):
                    # Read a bit of content to check
                    text = await resp.text()
                    not_found_markers = [
                        "page not found", "404", "doesn't exist",
                        "no user", "user not found", "nothing here",
                        "profile does not exist", "this account doesn",
                    ]
                    if any(m in text[:2000].lower() for m in not_found_markers):
                        is_real = False
                    if len(text) < 300:
                        is_real = False

                if is_real:
                    # Avoid duplicates (same platform)
                    existing = [p["platform"] for p in report.social_profiles]
                    if platform not in existing:
                        report.social_profiles.append({
                            "platform": platform,
                            "url": url,
                            "username": username,
                            "match_confidence": "high" if platform in ("GitHub", "Keybase") else "medium",
                        })
                        if platform not in report.data_sources:
                            report.data_sources.append(platform)

        except asyncio.TimeoutError:
            pass
        except Exception as e:
            self.logger.debug(f"{platform}/@{username}: {e}")

    # ===== Step 3: Deep GitHub Search =====

    async def _search_github_deep(self, report: PersonReport):
        """Search GitHub API for user details including repos, bio, company, location."""
        if not report.first_name:
            return

        name = f"{report.first_name} {report.last_name}"
        url = f"https://api.github.com/search/users?q={quote_plus(name)}+type:user&per_page=5"

        try:
            async with StealthSession() as stealth:
                resp = await stealth.get(url, headers={"Accept": "application/vnd.github.v3+json"})
                if resp.status != 200:
                    return
                data = await resp.json()

                for user in data.get("items", [])[:5]:
                    login = user.get("login", "")
                    # Fetch detailed user info
                    try:
                        await asyncio.sleep(_random_delay(0.3, 0.5))
                        detail_resp = await stealth.get(
                            f"https://api.github.com/users/{login}",
                            headers={"Accept": "application/vnd.github.v3+json"}
                        )
                        if detail_resp.status == 200:
                            details = await detail_resp.json()
                            profile = {
                                "platform": "GitHub",
                                "url": details.get("html_url", ""),
                                "username": login,
                                "name": details.get("name", ""),
                                "bio": details.get("bio", ""),
                                "company": details.get("company", ""),
                                "location": details.get("location", ""),
                                "blog": details.get("blog", ""),
                                "email": details.get("email", ""),
                                "public_repos": details.get("public_repos", 0),
                                "followers": details.get("followers", 0),
                                "created_at": details.get("created_at", ""),
                                "match_confidence": "high",
                            }

                            # Check if location matches
                            if report.location and details.get("location"):
                                if report.city.lower() in details["location"].lower():
                                    profile["match_confidence"] = "very high"

                            report.github_details.append(profile)

                            # Extract extra data
                            if details.get("email"):
                                email = details["email"]
                                if email not in report.possible_emails:
                                    report.possible_emails.insert(0, email)  # High priority

                            if details.get("company"):
                                company = details["company"].lstrip("@")
                                if company not in report.employers:
                                    report.employers.append(company)

                            if details.get("blog"):
                                report.web_mentions.append({
                                    "title": f"Blog/Website ({login})",
                                    "url": details["blog"],
                                    "source": "GitHub",
                                })

                            # Also add to social_profiles if not already there
                            existing_gh = [p for p in report.social_profiles if p.get("platform") == "GitHub"]
                            if not existing_gh:
                                report.social_profiles.append({
                                    "platform": "GitHub",
                                    "url": details.get("html_url", ""),
                                    "username": login,
                                    "match_confidence": profile["match_confidence"],
                                })

                    except Exception:
                        pass

                if data.get("items"):
                    report.data_sources.append("GitHub API")

        except Exception as e:
            self.logger.debug(f"GitHub deep search failed: {e}")

    # ===== Step 4: Gravatar Check =====

    async def _check_gravatar(self, report: PersonReport):
        """Check Gravatar for profile info linked to email hashes."""
        if not report.possible_emails:
            return

        async with StealthSession() as stealth:
            # Check top 5 most likely emails
            for email in report.possible_emails[:5]:
                email_hash = hashlib.md5(email.lower().strip().encode()).hexdigest()
                url = f"https://en.gravatar.com/{email_hash}.json"
                try:
                    resp = await stealth.get(url)
                    if resp.status == 200:
                        data = await resp.json()
                        entries = data.get("entry", [])
                        for entry in entries:
                            report.gravatar = {
                                "email": email,
                                "display_name": entry.get("displayName", ""),
                                "profile_url": entry.get("profileUrl", ""),
                                "thumbnail": entry.get("thumbnailUrl", ""),
                                "about": entry.get("aboutMe", ""),
                                "current_location": entry.get("currentLocation", ""),
                            }

                            # Extract accounts linked to Gravatar
                            for acct in entry.get("accounts", []):
                                domain = acct.get("domain", "")
                                acct_url = acct.get("url", "")
                                if acct_url:
                                    existing_urls = [p.get("url") for p in report.social_profiles]
                                    if acct_url not in existing_urls:
                                        report.social_profiles.append({
                                            "platform": acct.get("shortname", domain),
                                            "url": acct_url,
                                            "username": acct.get("username", ""),
                                            "match_confidence": "high",
                                            "source": "Gravatar",
                                        })

                            # Extract photos
                            for photo in entry.get("photos", []):
                                if photo.get("value"):
                                    report.gravatar["photo_url"] = photo["value"]

                            report.data_sources.append("Gravatar")
                            return  # Found one, that's enough

                except Exception:
                    continue

    # ===== Step 5: Search Engine Dorking =====

    async def _search_engine_dork(self, report: PersonReport):
        """Use Bing search with stealth headers to avoid CAPTCHA."""
        if not report.first_name or not report.last_name:
            return

        name = f"{report.first_name} {report.last_name}"
        location = report.location or ""

        dork_queries = [
            f'"{name}" {location}',
            f'"{name}" site:linkedin.com',
            f'"{name}" site:facebook.com',
            f'"{name}" resume OR cv OR portfolio',
            f'"{name}" email OR contact',
        ]

        async with StealthSession() as stealth:
            for query in dork_queries:
                try:
                    # Bing search endpoint — stealth headers avoid CAPTCHA
                    url = f"https://www.bing.com/search?q={quote_plus(query)}&count=10"
                    resp = await stealth.get(url, headers={
                        "Referer": "https://www.bing.com/",
                    })
                    if resp.status == 200:
                        text = await resp.text()
                        soup = BeautifulSoup(text, "html.parser")

                        # Bing results are in <li class="b_algo">
                        for result in soup.select("li.b_algo"):
                            link_tag = result.find("a")
                            snippet_tag = result.find("p") or result.find("div", class_="b_caption")

                            if link_tag:
                                href = link_tag.get("href", "")
                                title = link_tag.get_text(strip=True)
                                snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

                                if href and not href.startswith("/") and href.startswith("http"):
                                    # Check if this is a social profile
                                    social = self._classify_social_url(href)
                                    if social:
                                        existing_urls = [p.get("url", "") for p in report.social_profiles]
                                        if href not in existing_urls:
                                            report.social_profiles.append({
                                                "platform": social,
                                                "url": href,
                                                "match_confidence": "medium",
                                                "source": "Bing search",
                                            })
                                    else:
                                        # General web mention
                                        existing_urls = [m.get("url", "") for m in report.web_mentions]
                                        if href not in existing_urls:
                                            report.web_mentions.append({
                                                "title": title[:120],
                                                "url": href,
                                                "snippet": snippet[:250],
                                                "query": query,
                                                "source": "Bing",
                                            })

                                    # Extract emails from snippets
                                    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', snippet)
                                    for em in emails:
                                        if em not in report.possible_emails:
                                            report.possible_emails.insert(0, em)

                                    # Extract phone numbers from snippets
                                    phones = re.findall(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}', snippet)
                                    for phone in phones:
                                        cleaned = re.sub(r'[^\d+]', '', phone)
                                        if len(cleaned) >= 8 and cleaned not in report.phone_numbers:
                                            report.phone_numbers.append(phone.strip())

                        if report.web_mentions or report.social_profiles:
                            if "Bing" not in report.data_sources:
                                report.data_sources.append("Bing")

                    await asyncio.sleep(_random_delay(0.8, 1.5))  # Human-paced between queries

                except Exception as e:
                    self.logger.debug(f"Bing dork failed for '{query}': {e}")

    def _classify_social_url(self, url: str) -> Optional[str]:
        """Classify a URL as belonging to a social platform."""
        social_domains = {
            "linkedin.com": "LinkedIn", "facebook.com": "Facebook",
            "twitter.com": "Twitter/X", "x.com": "Twitter/X",
            "instagram.com": "Instagram", "github.com": "GitHub",
            "reddit.com": "Reddit", "pinterest.com": "Pinterest",
            "medium.com": "Medium", "tiktok.com": "TikTok",
            "youtube.com": "YouTube", "twitch.tv": "Twitch",
            "behance.net": "Behance", "dribbble.com": "Dribbble",
            "stackoverflow.com": "StackOverflow", "gitlab.com": "GitLab",
            "deviantart.com": "DeviantArt", "vimeo.com": "Vimeo",
            "flickr.com": "Flickr", "soundcloud.com": "SoundCloud",
            "quora.com": "Quora", "researchgate.net": "ResearchGate",
        }
        for domain, name in social_domains.items():
            if domain in url:
                return name
        return None

    # ===== Step 6: People-Finder Sites =====

    async def _search_people_sites(self, report: PersonReport):
        """Search people-finder sites with stealth browser headers."""
        if not report.first_name or not report.last_name:
            return

        first = report.first_name.lower()
        last = report.last_name.lower()
        location = report.city.lower().replace(" ", "-") if report.city else ""

        sites = [
            {"name": "ThatsThem",       "url": f"https://thatsthem.com/name/{first}-{last}/{location}"},
            {"name": "WhitePages",      "url": f"https://www.whitepages.com/name/{first}-{last}/{location or 'US'}"},
            {"name": "TruePeopleSearch","url": f"https://www.truepeoplesearch.com/results?name={first}+{last}&citystatezip={location}"},
            {"name": "FastPeopleSearch","url": f"https://www.fastpeoplesearch.com/name/{first}-{last}_{location}"},
            {"name": "PeekYou",         "url": f"https://www.peekyou.com/{first}_{last}"},
            {"name": "Radaris",         "url": f"https://radaris.com/p/{first}/{last}/"},
            {"name": "NZ WhitePages",   "url": f"https://www.whitepages.co.nz/search?query={first}+{last}"},
            {"name": "192.com (UK)",    "url": f"https://www.192.com/people/{first}-{last}/"},
        ]

        # Shuffle site order to avoid consistent request patterns
        random.shuffle(sites)

        async with StealthSession() as stealth:
            # Sequential with random delays — looks like a human browsing
            for s in sites:
                await self._check_people_site(stealth, s["name"], s["url"], report)
                await asyncio.sleep(_random_delay(0.5, 1.0))

    async def _check_people_site(self, stealth: StealthSession,
                                  site_name: str, url: str, report: PersonReport):
        try:
            resp = await stealth.get(url, headers={"Referer": "https://www.google.com/search?q="})
            if resp.status == 200:
                text = await resp.text()
                has_results = any(kw in text.lower() for kw in [
                    report.last_name.lower(), "age", "address", "phone",
                    "lives in", "associated", "has lived", "related to",
                ])
                if has_results and len(text) > 2000:
                    report.public_records.append({
                        "source": site_name, "url": url, "has_data": True,
                    })
                    report.data_sources.append(site_name)
                    self._extract_people_data(text, site_name, report)
        except Exception as e:
            self.logger.debug(f"{site_name}: {e}")

    def _extract_people_data(self, html: str, source: str, report: PersonReport):
        """Extract structured data from people search HTML."""
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)

        # Phone numbers (US format)
        for phone in re.findall(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text):
            cleaned = re.sub(r'[^\d]', '', phone)
            existing = [re.sub(r'[^\d]', '', p) for p in report.phone_numbers]
            if len(cleaned) == 10 and cleaned not in existing:
                report.phone_numbers.append(phone)

        # Phone numbers (international)
        for phone in re.findall(r'\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{3,4}[-.\s]?\d{3,4}', text):
            cleaned = re.sub(r'[^\d+]', '', phone)
            if cleaned not in [re.sub(r'[^\d+]', '', p) for p in report.phone_numbers]:
                report.phone_numbers.append(phone)

        # Addresses
        for addr in re.findall(
            r'\d+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:St|Ave|Rd|Dr|Ln|Blvd|Way|Ct|Pl|Cir)',
            html, re.IGNORECASE
        )[:5]:
            if addr not in report.addresses:
                report.addresses.append(addr)

        # Emails
        for email in re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', html):
            if email not in report.possible_emails and not email.endswith(('.png', '.jpg', '.gif', '.css', '.js')):
                report.possible_emails.insert(0, email)

        # Context extraction
        text_lower = text.lower()
        for label, target, keywords in [
            ("employers", report.employers, ["works at", "employed by", "company:", "employer:"]),
            ("education", report.education, ["attended", "graduated from", "university", "college"]),
            ("relatives", report.relatives, ["related to", "relatives:", "associated with"]),
        ]:
            for kw in keywords:
                idx = text_lower.find(kw)
                if idx != -1:
                    excerpt = text[idx:idx + 100].split("\n")[0].strip()
                    if len(excerpt) > 10 and excerpt[:80] not in target:
                        target.append(excerpt[:80])

    # ===== Step 7: Wayback Machine =====

    async def _search_wayback(self, report: PersonReport):
        """Search Wayback Machine CDX API."""
        if not report.first_name or not report.last_name:
            return

        query = f"{report.first_name.lower()}-{report.last_name.lower()}"
        url = f"https://web.archive.org/cdx/search/cdx?url=*/{query}*&output=json&limit=15&fl=timestamp,original,statuscode"

        try:
            async with StealthSession() as stealth:
                resp = await stealth.get(url)
                if resp.status == 200:
                    data = await resp.json()
                    if len(data) > 1:
                        for row in data[1:]:
                            if len(row) >= 3:
                                report.archived_pages.append({
                                    "timestamp": row[0],
                                    "url": row[1],
                                    "status": row[2],
                                    "archive_url": f"https://web.archive.org/web/{row[0]}/{row[1]}",
                                })
                        report.data_sources.append("Wayback Machine")
        except Exception as e:
            self.logger.debug(f"Wayback failed: {e}")

    # ===== Step 8: Breach Directory Check =====

    async def _check_breaches(self, report: PersonReport):
        """Check breach directory services for known email compromises."""
        if not report.possible_emails:
            return

        async with StealthSession() as stealth:
            # Check top 3 most likely emails against breach data
            for email in report.possible_emails[:3]:
                try:
                    # Use the XposedOrNot free API (no key required, CORS open)
                    url = f"https://api.xposedornot.com/v1/check-email/{quote(email)}"
                    resp = await stealth.get(url)
                    if resp.status == 200:
                        data = await resp.json()
                        breaches_list = data.get("breaches", [])
                        if breaches_list:
                            for breach in breaches_list[:10]:
                                report.breaches.append({
                                    "email": email,
                                    "breach": breach if isinstance(breach, str) else str(breach),
                                })
                            if "Breach Directory" not in report.data_sources:
                                report.data_sources.append("Breach Directory")
                except Exception:
                    pass

    # ===== Step 9: Email Validation =====

    async def _validate_emails(self, report: PersonReport):
        """Validate emails by checking MX records."""
        import dns.resolver

        validated = []
        checked_domains = {}

        for email in report.possible_emails[:30]:
            domain = email.split("@")[1]
            if domain not in checked_domains:
                try:
                    answers = dns.resolver.resolve(domain, "MX")
                    checked_domains[domain] = bool(answers)
                except Exception:
                    checked_domains[domain] = False

            if checked_domains.get(domain, False):
                validated.append(email)

        report.possible_emails = validated
        self.logger.info(f"{len(validated)} emails passed MX validation")

    # ===== Step 10: Confidence Scoring =====

    async def _calculate_confidence(self, report: PersonReport):
        """Calculate overall confidence score."""
        score = 0.0

        if report.social_profiles:
            score += min(len(report.social_profiles) * 6, 25)
        if report.github_details:
            score += min(len(report.github_details) * 8, 15)
        if report.public_records:
            score += min(len(report.public_records) * 8, 20)
        if report.web_mentions:
            score += min(len(report.web_mentions) * 4, 15)
        if report.phone_numbers:
            score += min(len(report.phone_numbers) * 8, 10)
        if report.addresses:
            score += min(len(report.addresses) * 5, 10)
        if report.archived_pages:
            score += 5
        if report.gravatar:
            score += 10
        if report.breaches:
            score += min(len(report.breaches) * 3, 10)
        if report.employers:
            score += min(len(report.employers) * 5, 10)


        report.confidence_score = min(score, 100)
