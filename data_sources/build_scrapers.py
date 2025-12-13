"""
Build Scrapers - Fetch popular builds from various sources

Supported sources:
- poe.ninja builds (top builds by DPS/popularity)
- pobb.in (PoB pastebin links)
- Direct PoB codes
"""
from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from core.constants import API_TIMEOUT_DEFAULT, API_TIMEOUT_STANDARD

# Allowed hosts for PoB code links
ALLOWED_POB_HOSTS = frozenset({
    'pastebin.com',
    'www.pastebin.com',
    'pobb.in',
    'www.pobb.in',
})


def is_allowed_pob_url(url: str) -> bool:
    """
    Check if a URL is from an allowed PoB hosting domain.

    Properly validates the hostname to prevent URL substring bypass attacks
    like 'evil.com/pastebin.com' or 'pastebin.com.evil.com'.

    Args:
        url: URL to validate

    Returns:
        True if the URL's host is in the allowed list
    """
    try:
        parsed = urlparse(url)
        # Check the actual hostname, not a substring match
        return parsed.netloc.lower() in ALLOWED_POB_HOSTS
    except (ValueError, AttributeError):
        return False


def _is_pobarchives_url(url: str) -> bool:
    """Check if URL is from pobarchives.com using proper hostname validation."""
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        return host == 'pobarchives.com' or host == 'www.pobarchives.com'
    except (ValueError, AttributeError):
        return False

logger = logging.getLogger(__name__)


@dataclass
class ScrapedBuild:
    """A build scraped from a website."""
    source: str  # "poe.ninja", "pobb.in", etc.
    build_name: str
    pob_code: Optional[str] = None

    # Build metadata
    char_class: Optional[str] = None
    ascendancy: Optional[str] = None
    main_skill: Optional[str] = None

    # Popularity metrics
    rank: Optional[int] = None
    dps: Optional[float] = None
    life: Optional[int] = None
    es: Optional[int] = None

    # Source URL
    url: Optional[str] = None
    scraped_at: datetime = field(default_factory=datetime.now)


class PoeNinjaBuildScraper:
    """
    Scrape builds from poe.ninja/builds

    Features:
    - Top builds by DPS
    - Top builds by popularity
    - Filter by league/class/skill
    """

    BASE_URL = "https://poe.ninja/builds"

    def __init__(self, league: str = "Ancestor", rate_limit: float = 2.0):
        """
        Initialize poe.ninja scraper.

        Args:
            league: League name (default: current league)
            rate_limit: Seconds between requests (default: 2.0)
        """
        self.league = league
        self.rate_limit = rate_limit
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PoE-Price-Checker/1.0 (Build Analysis Tool)'
        })
        self.last_request = 0.0

    def _wait_for_rate_limit(self) -> None:
        """Respect rate limiting."""
        elapsed = time.time() - self.last_request
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self.last_request = time.time()

    def scrape_top_builds(
        self,
        limit: int = 50,
        sort_by: str = "dps",  # "dps", "energy-shield", "life", etc.
        skill: Optional[str] = None,
        char_class: Optional[str] = None,
    ) -> List[ScrapedBuild]:
        """
        Scrape top builds from poe.ninja.

        Args:
            limit: Number of builds to fetch (max 100)
            sort_by: Sort criteria ("dps", "energy-shield", "life", "depth-solo")
            skill: Filter by skill name (optional)
            char_class: Filter by character class (optional)

        Returns:
            List of ScrapedBuild objects
        """
        self._wait_for_rate_limit()

        # Build URL with filters
        url = f"{self.BASE_URL}/{self.league}"
        params: Dict[str, Any] = {
            'sort': sort_by,
            'take': min(limit, 100)
        }

        if skill:
            params['skill'] = skill
        if char_class:
            params['class'] = char_class

        try:
            logger.info(f"Fetching top {limit} builds from poe.ninja (sort={sort_by})")
            response = self.session.get(url, params=params, timeout=API_TIMEOUT_STANDARD)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Find build entries
            # Note: poe.ninja structure may vary - this is a placeholder
            # You may need to inspect the actual page structure
            builds = []

            # Look for build data in JSON embedded in page
            # poe.ninja often embeds build data in <script> tags
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and 'builds' in script.string:
                    # Try to extract JSON data
                    # This is simplified - actual implementation may need regex/json parsing
                    logger.debug("Found potential build data in script tag")

            # Alternative: Use poe.ninja API directly
            # poe.ninja has an undocumented API we could use
            api_url = "https://poe.ninja/api/builds/overview"
            api_params = {
                'league': self.league,
                'type': 'depth-solo',  # or 'dps'
                'language': 'en'
            }

            logger.info(f"Trying poe.ninja API: {api_url}")
            api_response = self.session.get(api_url, params=api_params, timeout=API_TIMEOUT_STANDARD)

            if api_response.status_code == 200:
                data = api_response.json()

                # Parse build data from API response
                if 'builds' in data:
                    for build_data in data['builds'][:limit]:
                        build = ScrapedBuild(
                            source='poe.ninja',
                            build_name=build_data.get('name', 'Unknown'),
                            char_class=build_data.get('class', ''),
                            ascendancy=build_data.get('ascendancy', ''),
                            main_skill=build_data.get('mainSkill', ''),
                            rank=build_data.get('rank'),
                            dps=build_data.get('dps'),
                            life=build_data.get('life'),
                            es=build_data.get('energyShield'),
                            url=build_data.get('url', ''),
                        )
                        builds.append(build)
                        logger.debug(f"Scraped build: {build.build_name} ({build.main_skill})")

            logger.info(f"Scraped {len(builds)} builds from poe.ninja")
            return builds

        except requests.RequestException as e:
            logger.error(f"Failed to scrape poe.ninja: {e}")
            return []
        except (ValueError, KeyError, AttributeError) as e:
            logger.error(f"Failed to parse poe.ninja response: {e}")
            return []

    def get_pob_from_profile(self, profile_url: str) -> Optional[str]:
        """
        Try to extract PoB code from a poe.ninja profile page.

        Args:
            profile_url: URL to character profile

        Returns:
            PoB code if found, None otherwise
        """
        self._wait_for_rate_limit()

        try:
            logger.info(f"Fetching PoB from profile: {profile_url}")
            response = self.session.get(profile_url, timeout=API_TIMEOUT_STANDARD)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Look for PoB link or code
            # Common patterns:
            # - pastebin.com/raw/XXXXX
            # - pobb.in/XXXXX
            # - Direct PoB code in <textarea>

            links = soup.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                href_str = str(href) if href else ''
                if is_allowed_pob_url(href_str):
                    logger.info(f"Found PoB link: {href_str}")
                    return href_str

            # Look for embedded PoB code
            textareas = soup.find_all('textarea')
            for textarea in textareas:
                text = textarea.get_text().strip()
                # PoB codes are long base64 strings
                if len(text) > 100 and re.match(r'^[A-Za-z0-9+/=]+$', text):
                    logger.info("Found embedded PoB code")
                    return text

            logger.warning("No PoB code found in profile")
            return None

        except requests.RequestException as e:
            logger.error(f"Network error fetching profile: {e}")
            return None
        except (ValueError, AttributeError) as e:
            logger.error(f"Failed to parse profile page: {e}")
            return None


class PobbinScraper:
    """
    Fetch PoB codes from pobb.in (PoB pastebin).
    """

    BASE_URL = "https://pobb.in"

    def __init__(self, rate_limit: float = 1.0):
        """
        Initialize pobb.in scraper.

        Args:
            rate_limit: Seconds between requests (default: 1.0)
        """
        self.rate_limit = rate_limit
        self.session = requests.Session()
        self.last_request = 0.0

    def _wait_for_rate_limit(self) -> None:
        """Respect rate limiting."""
        elapsed = time.time() - self.last_request
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self.last_request = time.time()

    def get_pob_code(self, pobb_id: str) -> Optional[str]:
        """
        Fetch PoB code from pobb.in ID.

        Args:
            pobb_id: The pobb.in ID (e.g., "ABC123")

        Returns:
            PoB code string if successful, None otherwise
        """
        self._wait_for_rate_limit()

        # pobb.in API: /{id}/raw returns raw PoB code
        url = f"{self.BASE_URL}/{pobb_id}/raw"

        try:
            logger.info(f"Fetching PoB code from pobb.in: {pobb_id}")
            response = self.session.get(url, timeout=API_TIMEOUT_DEFAULT)
            response.raise_for_status()

            pob_code = response.text.strip()

            # Validate it looks like a PoB code
            if len(pob_code) > 100 and re.match(r'^[A-Za-z0-9+/=]+$', pob_code):
                logger.info(f"Successfully fetched PoB code ({len(pob_code)} chars)")
                return pob_code
            else:
                logger.warning("Invalid PoB code format from pobb.in")
                return None

        except requests.RequestException as e:
            logger.error(f"Failed to fetch from pobb.in: {e}")
            return None

    def get_pob_from_url(self, url: str) -> Optional[str]:
        """
        Extract PoB code from a pobb.in URL.

        Args:
            url: Full pobb.in URL (e.g., "https://pobb.in/ABC123")

        Returns:
            PoB code if successful, None otherwise
        """
        # Extract ID from URL
        match = re.search(r'pobb\.in/([A-Za-z0-9_-]+)', url)
        if match:
            pobb_id = match.group(1)
            return self.get_pob_code(pobb_id)
        else:
            logger.error(f"Invalid pobb.in URL: {url}")
            return None


class PoBArchivesScraper:
    """
    Scrape builds from pobarchives.com.

    Features:
    - Popular builds with pobb.in links
    - Filter by category (League Starter, SSF, Hardcore, etc.)
    - YouTube/Reddit popularity metrics
    """

    BASE_URL = "https://pobarchives.com"

    # Supported build categories/tags
    CATEGORIES = {
        "league_starter": "League Starter",
        "ssf": "SSF",
        "hardcore": "Hardcore",
        "mapping": "Mapping",
        "bossing": "Bossing",
        "budget": "Budget",
        "endgame": "Endgame",
    }

    # League/tree version options
    LEAGUES = {
        # PoE1
        "poe1_current": "3.27",  # Keepers of the Flame
        "poe1_3.27": "3.27",
        "poe1_3.26": "3.26",  # Phrecia
        "poe1_3.25": "3.25",  # Settlers of Kalguur
        # PoE2
        "poe2_current": "poe2-0.2.0",  # Third Edict
        "poe2_dawn": "poe2-0.1.1",  # Dawn of the Hunt
        "poe2_ea": "poe2-0.1.0",  # Early Access
    }

    def __init__(self, rate_limit: float = 2.0):
        """
        Initialize pobarchives.com scraper.

        Args:
            rate_limit: Seconds between requests (default: 2.0)
        """
        self.rate_limit = rate_limit
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PoE-Price-Checker/1.0 (Build Analysis Tool)',
            'Accept': 'application/json, text/html',
        })
        self.last_request = 0.0
        self._pobbin_scraper = PobbinScraper(rate_limit=rate_limit)

    def _wait_for_rate_limit(self) -> None:
        """Respect rate limiting."""
        elapsed = time.time() - self.last_request
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self.last_request = time.time()

    def scrape_builds_by_category(
        self,
        category: str,
        limit: int = 20,
        league: str = "poe1_current",
        fetch_pob_codes: bool = False,
    ) -> List[ScrapedBuild]:
        """
        Scrape builds from pobarchives.com by category.

        Args:
            category: Category key (e.g., "league_starter", "ssf", "hardcore")
            limit: Maximum number of builds to fetch (default: 20)
            league: League key from LEAGUES dict, or raw version string (default: "poe1_current")
            fetch_pob_codes: If True, also fetch PoB codes from pobb.in (slower)

        Returns:
            List of ScrapedBuild objects
        """
        if category not in self.CATEGORIES:
            logger.warning(f"Unknown category '{category}', using as raw tag")
            tag = category
        else:
            tag = self.CATEGORIES[category]

        # Resolve league to tree version
        tree_version = self.LEAGUES.get(league, league)

        self._wait_for_rate_limit()

        # Build URL with filters
        # pobarchives uses JSON-encoded tags in URL
        import json
        tags_param = json.dumps([tag])
        url = f"{self.BASE_URL}/builds/poe"
        params = {
            'tags': tags_param,
            'tree': tree_version,
            'sort': 'popularity',
        }

        try:
            logger.info(f"Fetching {category} builds from pobarchives.com")
            response = self.session.get(url, params=params, timeout=API_TIMEOUT_STANDARD)
            response.raise_for_status()

            # Parse HTML to find build data
            soup = BeautifulSoup(response.text, 'html.parser')
            builds = self._parse_build_listings(soup, limit, category)

            # Optionally fetch pobb.in URLs and PoB codes
            if fetch_pob_codes:
                for build in builds:
                    # Check if URL is from pobarchives using proper hostname validation
                    if build.url and _is_pobarchives_url(build.url):
                        # First get pobb.in URL from build page
                        pobb_url = self._fetch_pobb_url_from_build_page(build.url)
                        if pobb_url:
                            build.url = pobb_url  # Replace internal URL with pobb.in
                            # Then fetch actual PoB code
                            pob_code = self._pobbin_scraper.get_pob_from_url(pobb_url)
                            if pob_code:
                                build.pob_code = pob_code

            logger.info(f"Scraped {len(builds)} {category} builds from pobarchives.com")
            return builds

        except requests.RequestException as e:
            logger.error(f"Failed to scrape pobarchives.com: {e}")
            return []
        except (ValueError, KeyError, AttributeError) as e:
            logger.error(f"Failed to parse pobarchives.com response: {e}")
            return []

    def _parse_build_listings(
        self,
        soup: BeautifulSoup,
        limit: int,
        category: str,
    ) -> List[ScrapedBuild]:
        """
        Parse build listings from pobarchives.com HTML.

        Args:
            soup: BeautifulSoup parsed HTML
            limit: Maximum builds to return
            category: Category being scraped (for metadata)

        Returns:
            List of ScrapedBuild objects
        """
        builds: List[ScrapedBuild] = []

        # pobarchives.com uses internal build IDs, not direct pobb.in links
        # Structure: <article class="listing-style1">
        #   <a href="/build/mciA7nQh">
        #     <h6 class="list-title">Build Name</h6>
        #   </a>
        #   <img alt="Ascendancy" />
        # </article>

        # Find internal build links
        build_links = soup.find_all('a', href=re.compile(r'^/build/[A-Za-z0-9_-]+$'))

        # Common ascendancies for detection
        ascendancies = [
            "Slayer", "Gladiator", "Champion",  # Duelist
            "Assassin", "Saboteur", "Trickster",  # Shadow
            "Juggernaut", "Berserker", "Chieftain",  # Marauder
            "Necromancer", "Elementalist", "Occultist",  # Witch
            "Deadeye", "Raider", "Pathfinder",  # Ranger
            "Inquisitor", "Hierophant", "Guardian",  # Templar
            "Ascendant",  # Scion
        ]

        seen_ids = set()
        for link in build_links:
            if len(builds) >= limit:
                break

            href_raw = link.get('href', '')
            href = str(href_raw) if href_raw else ''
            build_id = href.replace('/build/', '')

            # Skip duplicates
            if build_id in seen_ids:
                continue
            seen_ids.add(build_id)

            # Get build name from title element
            build_name = "Unknown Build"
            title_elem = link.find(['h6', 'h5', 'h4', 'h3'])
            if title_elem:
                build_name = title_elem.get_text(strip=True)
            elif link.get_text(strip=True):
                build_name = link.get_text(strip=True)

            # Try to extract ascendancy from alt text or nearby elements
            ascendancy: Optional[str] = None
            parent = link.find_parent(['article', 'div'])
            if parent:
                # Look for ascendancy icon alt text
                img = parent.find('img', alt=True)
                if img:
                    img_alt = str(img.get('alt', ''))
                    if img_alt in ascendancies:
                        ascendancy = img_alt
                if ascendancy is None:
                    # Check title text for ascendancy
                    for asc in ascendancies:
                        if asc.lower() in build_name.lower():
                            ascendancy = asc
                            break

            # Store internal URL - will need separate fetch to get pobb.in link
            internal_url = f"https://pobarchives.com{href}"

            build = ScrapedBuild(
                source='pobarchives.com',
                build_name=build_name,
                pob_code=None,  # Fetched later if requested
                char_class=None,
                ascendancy=ascendancy,
                main_skill=None,
                url=internal_url,  # Internal URL, not pobb.in yet
            )
            builds.append(build)
            logger.debug(f"Found build: {build_name} ({ascendancy}) -> {internal_url}")

        return builds

    def _fetch_pobb_url_from_build_page(self, internal_url: str) -> Optional[str]:
        """
        Fetch pobb.in URL from individual build page.

        Args:
            internal_url: pobarchives.com internal build URL

        Returns:
            First pobb.in URL found, or None
        """
        self._wait_for_rate_limit()

        try:
            response = self.session.get(internal_url, timeout=API_TIMEOUT_STANDARD)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find pobb.in links
            pobb_links = soup.find_all('a', href=re.compile(r'pobb\.in/[A-Za-z0-9_-]+'))
            if pobb_links:
                pobb_url_raw = pobb_links[0].get('href', '')
                pobb_url = str(pobb_url_raw) if pobb_url_raw else ''
                if pobb_url and not pobb_url.startswith('http'):
                    pobb_url = 'https://' + pobb_url.lstrip('/')
                return pobb_url if pobb_url else None

            return None

        except requests.RequestException as e:
            logger.error(f"Network error fetching pobb.in URL from {internal_url}: {e}")
            return None
        except (ValueError, AttributeError) as e:
            logger.error(f"Failed to parse pobb.in URL from {internal_url}: {e}")
            return None

    def scrape_all_categories(
        self,
        categories: Optional[List[str]] = None,
        limit_per_category: int = 20,
        league: str = "poe1_current",
        fetch_pob_codes: bool = False,
    ) -> dict:
        """
        Scrape builds from multiple categories.

        Args:
            categories: List of category keys, or None for all
            limit_per_category: Max builds per category (default: 20)
            league: League key from LEAGUES dict (default: "poe1_current")
            fetch_pob_codes: If True, also fetch PoB codes

        Returns:
            Dict mapping category -> List[ScrapedBuild]
        """
        if categories is None:
            categories = list(self.CATEGORIES.keys())

        results = {}
        for category in categories:
            builds = self.scrape_builds_by_category(
                category=category,
                limit=limit_per_category,
                league=league,
                fetch_pob_codes=fetch_pob_codes,
            )
            results[category] = builds

        total = sum(len(b) for b in results.values())
        logger.info(f"Scraped {total} builds across {len(categories)} categories")
        return results


class PastebinScraper:
    """
    Fetch PoB codes from pastebin.com.
    """

    BASE_URL = "https://pastebin.com"

    def __init__(self, rate_limit: float = 1.0):
        """Initialize pastebin scraper."""
        self.rate_limit = rate_limit
        self.session = requests.Session()
        self.last_request = 0.0

    def _wait_for_rate_limit(self) -> None:
        """Respect rate limiting."""
        elapsed = time.time() - self.last_request
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self.last_request = time.time()

    def get_pob_code(self, paste_id: str) -> Optional[str]:
        """
        Fetch PoB code from pastebin.

        Args:
            paste_id: Pastebin paste ID

        Returns:
            PoB code if successful, None otherwise
        """
        self._wait_for_rate_limit()

        # Use raw endpoint
        url = f"{self.BASE_URL}/raw/{paste_id}"

        try:
            logger.info(f"Fetching PoB code from pastebin: {paste_id}")
            response = self.session.get(url, timeout=API_TIMEOUT_DEFAULT)
            response.raise_for_status()

            pob_code = response.text.strip()

            # Validate
            if len(pob_code) > 100:
                logger.info(f"Successfully fetched PoB code ({len(pob_code)} chars)")
                return pob_code
            else:
                logger.warning("Retrieved text too short to be PoB code")
                return None

        except requests.RequestException as e:
            logger.error(f"Network error fetching from pastebin: {e}")
            return None


class BuildSourceProvider:
    """
    Provides URLs to external build sources for browsing.

    These sites use JavaScript rendering making direct scraping difficult,
    but we can provide direct links for users to browse.
    """

    # Build source URLs with filtering support
    SOURCES = {
        "pobarchives": {
            "name": "PoB Archives",
            "base_url": "https://pobarchives.com/builds/poe",
            "description": "Community builds with pobb.in links",
            "has_filtering": True,
        },
        "mobalytics": {
            "name": "Mobalytics",
            "base_url": "https://mobalytics.gg/poe/starter-builds",
            "description": "Curated starter builds with guides",
            "has_filtering": False,
        },
        "poeninja": {
            "name": "poe.ninja Builds",
            "base_url": "https://poe.ninja/builds",
            "description": "Ladder character builds",
            "has_filtering": True,
        },
        "maxroll": {
            "name": "Maxroll.gg",
            "base_url": "https://maxroll.gg/poe/build-guides",
            "description": "In-depth build guides",
            "has_filtering": True,
        },
    }

    @classmethod
    def get_source_url(
        cls,
        source: str,
        category: Optional[str] = None,
        league: str = "3.27",
    ) -> Optional[str]:
        """
        Get URL for a build source with optional filtering.

        Args:
            source: Source key (pobarchives, mobalytics, etc.)
            category: Category filter (league_starter, ssf, etc.)
            league: League/tree version

        Returns:
            URL string or None if source not found
        """
        if source not in cls.SOURCES:
            return None

        source_info = cls.SOURCES[source]
        url = str(source_info["base_url"])

        # Add filters for supported sources
        if source == "pobarchives" and category:
            import json
            import urllib.parse
            category_map = {
                "league_starter": "League Starter",
                "ssf": "SSF",
                "hardcore": "Hardcore",
                "mapping": "Mapping",
                "bossing": "Bossing",
            }
            tag = category_map.get(category, category)
            tags_param = urllib.parse.quote(json.dumps([tag]))
            url = f"{url}?tags={tags_param}&tree={league}&sort=popularity"

        return url

    @classmethod
    def get_all_sources(cls) -> dict:
        """Get info about all available build sources."""
        return cls.SOURCES.copy()


def extract_pob_link(text: str) -> Optional[str]:
    """
    Extract PoB link from text (forum posts, reddit, etc.).

    Args:
        text: Text potentially containing PoB link

    Returns:
        PoB link if found, None otherwise
    """
    # Common patterns
    patterns = [
        r'https?://pobb\.in/[A-Za-z0-9_-]+',
        r'https?://pastebin\.com/[A-Za-z0-9]+',
        r'pobb\.in/[A-Za-z0-9_-]+',
        r'pastebin\.com/[A-Za-z0-9]+',
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            link = match.group(0)
            # Ensure it has http(s)://
            if not link.startswith('http'):
                link = 'https://' + link
            return link

    return None


if __name__ == "__main__":
    # Test scrapers
    logging.basicConfig(level=logging.INFO)

    print("Testing Build Scrapers")
    print("=" * 80)

    # Test pobarchives.com scraper
    print("\n1. Testing pobarchives.com scraper...")
    archives_scraper = PoBArchivesScraper()

    print("  Available categories:", list(archives_scraper.CATEGORIES.keys()))

    # Test single category
    print("\n  Fetching League Starter builds...")
    starter_builds = archives_scraper.scrape_builds_by_category(
        category="league_starter",
        limit=5,
        fetch_pob_codes=False,  # Don't fetch codes for quick test
    )

    if starter_builds:
        print(f"  Found {len(starter_builds)} League Starter builds:")
        for i, build in enumerate(starter_builds, 1):
            print(f"    {i}. {build.build_name}")
            print(f"       Ascendancy: {build.ascendancy or 'Unknown'}")
            print(f"       URL: {build.url}")
    else:
        print("  No builds found (site structure may have changed)")

    # Test pobb.in scraper
    print("\n2. Testing pobb.in scraper...")
    if starter_builds and starter_builds[0].url:
        pobbin = PobbinScraper()
        print(f"  Testing with URL: {starter_builds[0].url}")
        pob_code = pobbin.get_pob_from_url(starter_builds[0].url)
        if pob_code:
            print(f"  Successfully fetched PoB code ({len(pob_code)} chars)")
            print(f"  First 50 chars: {pob_code[:50]}...")
        else:
            print("  Failed to fetch PoB code")
    else:
        print("  (Skipped - no build URL available)")

    # Test link extraction
    print("\n3. Testing link extraction...")
    test_text = "Check out my build: https://pobb.in/ABC123 or pastebin.com/XYZ789"
    link = extract_pob_link(test_text)
    print(f"  Extracted link: {link}")

    print("\n" + "=" * 80)
