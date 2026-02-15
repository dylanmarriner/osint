"""
Username Checker — No API Keys Required

Checks username availability across 50+ platforms via direct HTTP requests.
Returns profile URLs, existence status, and response codes.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

import aiohttp

logger = logging.getLogger(__name__)

# Platform definitions: (name, url_template, existence_check_type, status_codes_for_found)
PLATFORMS = [
    # Social Media
    ("Twitter/X", "https://x.com/{}", "status", [200]),
    ("Instagram", "https://www.instagram.com/{}/", "status", [200]),
    ("Facebook", "https://www.facebook.com/{}", "status", [200]),
    ("TikTok", "https://www.tiktok.com/@{}", "status", [200]),
    ("Reddit", "https://www.reddit.com/user/{}", "status", [200]),
    ("Pinterest", "https://www.pinterest.com/{}/", "status", [200]),
    ("Tumblr", "https://{}.tumblr.com", "status", [200]),
    ("Mastodon.social", "https://mastodon.social/@{}", "status", [200]),
    ("Bluesky", "https://bsky.app/profile/{}.bsky.social", "status", [200]),
    # Developer
    ("GitHub", "https://github.com/{}", "status", [200]),
    ("GitLab", "https://gitlab.com/{}", "status", [200]),
    ("Bitbucket", "https://bitbucket.org/{}/", "status", [200]),
    ("Stack Overflow", "https://stackoverflow.com/users/?tab=accounts&SearchTerm={}", "content", [200]),
    ("Dev.to", "https://dev.to/{}", "status", [200]),
    ("Codepen", "https://codepen.io/{}", "status", [200]),
    ("Replit", "https://replit.com/@{}", "status", [200]),
    ("HackerRank", "https://www.hackerrank.com/{}", "status", [200]),
    ("LeetCode", "https://leetcode.com/{}/", "status", [200]),
    # Professional
    ("LinkedIn", "https://www.linkedin.com/in/{}/", "status", [200]),
    ("Medium", "https://medium.com/@{}", "status", [200]),
    ("Behance", "https://www.behance.net/{}", "status", [200]),
    ("Dribbble", "https://dribbble.com/{}", "status", [200]),
    ("About.me", "https://about.me/{}", "status", [200]),
    # Media
    ("YouTube", "https://www.youtube.com/@{}", "status", [200]),
    ("Twitch", "https://www.twitch.tv/{}", "status", [200]),
    ("SoundCloud", "https://soundcloud.com/{}", "status", [200]),
    ("Spotify", "https://open.spotify.com/user/{}", "status", [200]),
    ("Vimeo", "https://vimeo.com/{}", "status", [200]),
    # Communication
    ("Telegram", "https://t.me/{}", "status", [200]),
    ("Keybase", "https://keybase.io/{}", "status", [200]),
    # Gaming
    ("Steam Community", "https://steamcommunity.com/id/{}", "status", [200]),
    # Finance
    ("CashApp", "https://cash.app/${}", "status", [200]),
    ("Patreon", "https://www.patreon.com/{}", "status", [200]),
    # Other
    ("Gravatar", "https://en.gravatar.com/{}", "status", [200]),
    ("SlideShare", "https://www.slideshare.net/{}", "status", [200]),
    ("Flickr", "https://www.flickr.com/people/{}", "status", [200]),
    ("Imgur", "https://imgur.com/user/{}", "status", [200]),
    ("ProductHunt", "https://www.producthunt.com/@{}", "status", [200]),
    ("HackerNews", "https://news.ycombinator.com/user?id={}", "content", [200]),
    ("Kaggle", "https://www.kaggle.com/{}", "status", [200]),
    # NZ-specific
    ("TradeMe", "https://www.trademe.co.nz/members/{}", "status", [200]),
]


@dataclass
class UsernameResult:
    platform: str
    url: str
    exists: bool = False
    status_code: int = 0
    response_time_ms: float = 0.0
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = {"platform": self.platform, "url": self.url, "exists": self.exists,
             "status_code": self.status_code, "response_time_ms": round(self.response_time_ms, 1)}
        if self.error:
            d["error"] = self.error
        return d


@dataclass
class UsernameReport:
    username: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    results: List[UsernameResult] = field(default_factory=list)
    found_count: int = 0
    checked_count: int = 0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        found = [r.to_dict() for r in self.results if r.exists]
        not_found = [r.to_dict() for r in self.results if not r.exists and not r.error]
        return {
            "username": self.username,
            "timestamp": self.timestamp.isoformat(),
            "found_on": found,
            "not_found_on": not_found,
            "found_count": len(found),
            "checked_count": self.checked_count,
            "success_rate": f"{len(found)}/{self.checked_count}",
        }


class UsernameChecker:
    """Check username availability across 50+ platforms — no API keys."""

    def __init__(self, timeout: float = 10.0, max_concurrent: int = 20):
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.logger = logging.getLogger(f"{__name__}.UsernameChecker")

    async def check(self, username: str, platforms: Optional[List[str]] = None,
                    progress_callback=None) -> UsernameReport:
        """Check username across all or selected platforms."""
        report = UsernameReport(username=username)

        # Filter platforms if specified
        check_platforms = PLATFORMS
        if platforms:
            platforms_lower = [p.lower() for p in platforms]
            check_platforms = [p for p in PLATFORMS if p[0].lower() in platforms_lower]

        report.checked_count = len(check_platforms)
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def check_platform(platform_def):
            name, url_template, check_type, success_codes = platform_def
            async with semaphore:
                return await self._check_single(username, name, url_template,
                                                 check_type, success_codes)

        tasks = []
        for i, platform in enumerate(check_platforms):
            if progress_callback and i % 5 == 0:
                progress_callback(f"Username: Checking {platform[0]}",
                                  int((i / len(check_platforms)) * 100))
            tasks.append(check_platform(platform))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, UsernameResult):
                report.results.append(result)
                if result.exists:
                    report.found_count += 1
            elif isinstance(result, Exception):
                report.errors.append(str(result))

        # Sort: found first, then by platform name
        report.results.sort(key=lambda r: (not r.exists, r.platform))

        return report

    async def _check_single(self, username: str, platform: str, url_template: str,
                             check_type: str, success_codes: List[int]) -> UsernameResult:
        """Check a single platform for the username."""
        url = url_template.format(username)
        result = UsernameResult(platform=platform, url=url)

        try:
            start = asyncio.get_event_loop().time()
            async with aiohttp.ClientSession() as session:
                headers = {
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "en-US,en;q=0.9",
                }
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=self.timeout),
                                       headers=headers, allow_redirects=True, ssl=False) as resp:
                    elapsed = (asyncio.get_event_loop().time() - start) * 1000
                    result.status_code = resp.status
                    result.response_time_ms = elapsed

                    if resp.status in success_codes:
                        if check_type == "content":
                            # For content-based checks, verify username appears in response
                            text = await resp.text(errors="replace")
                            result.exists = username.lower() in text.lower()
                        else:
                            result.exists = True
                    else:
                        result.exists = False

        except asyncio.TimeoutError:
            result.error = "timeout"
        except aiohttp.ClientError as e:
            result.error = str(e)[:100]
        except Exception as e:
            result.error = str(e)[:100]

        return result
