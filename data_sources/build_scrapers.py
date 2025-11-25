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
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

import requests
from bs4 import BeautifulSoup

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
        params = {
            'sort': sort_by,
            'take': min(limit, 100)
        }

        if skill:
            params['skill'] = skill
        if char_class:
            params['class'] = char_class

        try:
            logger.info(f"Fetching top {limit} builds from poe.ninja (sort={sort_by})")
            response = self.session.get(url, params=params, timeout=15)
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
                    logger.debug(f"Found potential build data in script tag")

            # Alternative: Use poe.ninja API directly
            # poe.ninja has an undocumented API we could use
            api_url = f"https://poe.ninja/api/builds/overview"
            api_params = {
                'league': self.league,
                'type': 'depth-solo',  # or 'dps'
                'language': 'en'
            }

            logger.info(f"Trying poe.ninja API: {api_url}")
            api_response = self.session.get(api_url, params=api_params, timeout=15)

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
        except Exception as e:
            logger.error(f"Unexpected error scraping poe.ninja: {e}")
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
            response = self.session.get(profile_url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Look for PoB link or code
            # Common patterns:
            # - pastebin.com/raw/XXXXX
            # - pobb.in/XXXXX
            # - Direct PoB code in <textarea>

            links = soup.find_all('a', href=True)
            for link in links:
                href = link['href']
                if 'pastebin.com' in href or 'pobb.in' in href:
                    logger.info(f"Found PoB link: {href}")
                    return href

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

        except Exception as e:
            logger.error(f"Failed to get PoB from profile: {e}")
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

        # pobb.in has a raw endpoint
        url = f"{self.BASE_URL}/raw/{pobb_id}"

        try:
            logger.info(f"Fetching PoB code from pobb.in: {pobb_id}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            pob_code = response.text.strip()

            # Validate it looks like a PoB code
            if len(pob_code) > 100 and re.match(r'^[A-Za-z0-9+/=]+$', pob_code):
                logger.info(f"Successfully fetched PoB code ({len(pob_code)} chars)")
                return pob_code
            else:
                logger.warning(f"Invalid PoB code format from pobb.in")
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
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            pob_code = response.text.strip()

            # Validate
            if len(pob_code) > 100:
                logger.info(f"Successfully fetched PoB code ({len(pob_code)} chars)")
                return pob_code
            else:
                logger.warning("Retrieved text too short to be PoB code")
                return None

        except Exception as e:
            logger.error(f"Failed to fetch from pastebin: {e}")
            return None


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

    # Test poe.ninja
    print("\n1. Testing poe.ninja scraper...")
    ninja_scraper = PoeNinjaBuildScraper(league="Ancestor")
    builds = ninja_scraper.scrape_top_builds(limit=5, sort_by="dps")

    if builds:
        print(f"Found {len(builds)} builds:")
        for i, build in enumerate(builds, 1):
            print(f"  {i}. {build.build_name} - {build.main_skill}")
            print(f"     Class: {build.char_class}/{build.ascendancy}")
            print(f"     DPS: {build.dps}, Life: {build.life}, ES: {build.es}")
    else:
        print("  No builds found (API may have changed)")

    # Test pobb.in (need a valid ID to test)
    print("\n2. Testing pobb.in scraper...")
    print("  (Skipped - need valid pobb.in ID)")

    # Test link extraction
    print("\n3. Testing link extraction...")
    test_text = "Check out my build: https://pobb.in/ABC123 or pastebin.com/XYZ789"
    link = extract_pob_link(test_text)
    print(f"  Extracted link: {link}")

    print("\n" + "=" * 80)
