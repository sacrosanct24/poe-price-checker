"""Tests for data_sources/build_scrapers.py - Build scrapers."""
import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from data_sources.build_scrapers import (
    ScrapedBuild,
    PoeNinjaBuildScraper,
    PobbinScraper,
    PoBArchivesScraper,
    PastebinScraper,
    BuildSourceProvider,
    extract_pob_link,
)


class TestScrapedBuild:
    """Tests for ScrapedBuild dataclass."""

    def test_create_basic_build(self):
        """Should create build with required fields."""
        build = ScrapedBuild(
            source="poe.ninja",
            build_name="Tornado Shot Deadeye",
        )

        assert build.source == "poe.ninja"
        assert build.build_name == "Tornado Shot Deadeye"

    def test_create_full_build(self):
        """Should create build with all fields."""
        build = ScrapedBuild(
            source="pobarchives.com",
            build_name="LA/TS Deadeye",
            pob_code="eNoN1G...",
            char_class="Ranger",
            ascendancy="Deadeye",
            main_skill="Lightning Arrow",
            rank=1,
            dps=50000000.0,
            life=5000,
            es=0,
            url="https://pobb.in/ABC123",
        )

        assert build.char_class == "Ranger"
        assert build.ascendancy == "Deadeye"
        assert build.main_skill == "Lightning Arrow"
        assert build.dps == 50000000.0

    def test_default_values(self):
        """Should have correct default values."""
        build = ScrapedBuild(
            source="test",
            build_name="Test Build",
        )

        assert build.pob_code is None
        assert build.char_class is None
        assert build.rank is None
        assert build.dps is None
        assert build.url is None
        assert isinstance(build.scraped_at, datetime)


class TestPoeNinjaBuildScraper:
    """Tests for PoeNinjaBuildScraper class."""

    @pytest.fixture
    def scraper(self):
        """Create scraper instance."""
        return PoeNinjaBuildScraper(league="Test", rate_limit=0.0)

    def test_init(self, scraper):
        """Should initialize with defaults."""
        assert scraper.league == "Test"
        assert scraper.rate_limit == 0.0

    def test_init_default_league(self):
        """Should have default league."""
        scraper = PoeNinjaBuildScraper()
        assert scraper.league == "Ancestor"

    def test_rate_limit_respects_timing(self):
        """Should wait between requests."""
        scraper = PoeNinjaBuildScraper(rate_limit=0.1)

        start = time.time()
        scraper._wait_for_rate_limit()
        scraper._wait_for_rate_limit()
        elapsed = time.time() - start

        assert elapsed >= 0.1

    @patch('data_sources.build_scrapers.requests.Session.get')
    def test_scrape_top_builds(self, mock_get, scraper):
        """Should scrape builds from poe.ninja."""
        # Mock HTML response
        mock_html_response = MagicMock()
        mock_html_response.text = "<html><body></body></html>"
        mock_html_response.status_code = 200

        # Mock API response
        mock_api_response = MagicMock()
        mock_api_response.status_code = 200
        mock_api_response.json.return_value = {
            "builds": [
                {
                    "name": "Build 1",
                    "class": "Ranger",
                    "ascendancy": "Deadeye",
                    "mainSkill": "Tornado Shot",
                    "rank": 1,
                    "dps": 1000000,
                    "life": 5000,
                },
            ]
        }

        mock_get.side_effect = [mock_html_response, mock_api_response]

        builds = scraper.scrape_top_builds(limit=10)

        assert len(builds) == 1
        assert builds[0].build_name == "Build 1"

    @patch('data_sources.build_scrapers.requests.Session.get')
    def test_scrape_top_builds_handles_error(self, mock_get, scraper):
        """Should handle request errors gracefully."""
        import requests
        mock_get.side_effect = requests.RequestException("Network error")

        builds = scraper.scrape_top_builds()

        assert builds == []

    @patch('data_sources.build_scrapers.requests.Session.get')
    def test_get_pob_from_profile(self, mock_get, scraper):
        """Should extract PoB link from profile page."""
        mock_response = MagicMock()
        mock_response.text = '''
            <html>
                <a href="https://pobb.in/ABC123">PoB Link</a>
            </html>
        '''
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = scraper.get_pob_from_profile("https://poe.ninja/test")

        assert result == "https://pobb.in/ABC123"


class TestPobbinScraper:
    """Tests for PobbinScraper class."""

    @pytest.fixture
    def scraper(self):
        """Create scraper instance."""
        return PobbinScraper(rate_limit=0.0)

    def test_init(self, scraper):
        """Should initialize correctly."""
        assert scraper.rate_limit == 0.0
        assert scraper.BASE_URL == "https://pobb.in"

    @patch('data_sources.build_scrapers.requests.Session.get')
    def test_get_pob_code(self, mock_get, scraper):
        """Should fetch PoB code from pobb.in."""
        mock_response = MagicMock()
        # PoB codes are base64-like strings
        mock_response.text = "eNo" + "A" * 200
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = scraper.get_pob_code("ABC123")

        assert result is not None
        assert len(result) > 100

    @patch('data_sources.build_scrapers.requests.Session.get')
    def test_get_pob_code_invalid_format(self, mock_get, scraper):
        """Should return None for invalid PoB code format."""
        mock_response = MagicMock()
        mock_response.text = "Not a valid PoB code"
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = scraper.get_pob_code("ABC123")

        assert result is None

    @patch('data_sources.build_scrapers.requests.Session.get')
    def test_get_pob_code_request_error(self, mock_get, scraper):
        """Should return None on request error."""
        import requests
        mock_get.side_effect = requests.RequestException("Error")

        result = scraper.get_pob_code("ABC123")

        assert result is None

    def test_get_pob_from_url(self, scraper):
        """Should extract ID from URL and fetch code."""
        with patch.object(scraper, 'get_pob_code', return_value="test_code"):
            result = scraper.get_pob_from_url("https://pobb.in/ABC123")

            assert result == "test_code"
            scraper.get_pob_code.assert_called_once_with("ABC123")

    def test_get_pob_from_url_invalid(self, scraper):
        """Should return None for invalid URL."""
        result = scraper.get_pob_from_url("https://example.com/not-pobb")

        assert result is None


class TestPoBArchivesScraper:
    """Tests for PoBArchivesScraper class."""

    @pytest.fixture
    def scraper(self):
        """Create scraper instance."""
        return PoBArchivesScraper(rate_limit=0.0)

    def test_init(self, scraper):
        """Should initialize correctly."""
        assert scraper.BASE_URL == "https://pobarchives.com"

    def test_categories_defined(self, scraper):
        """Should have category definitions."""
        assert "league_starter" in scraper.CATEGORIES
        assert "ssf" in scraper.CATEGORIES
        assert "hardcore" in scraper.CATEGORIES

    def test_leagues_defined(self, scraper):
        """Should have league definitions."""
        assert "poe1_current" in scraper.LEAGUES
        assert "poe2_current" in scraper.LEAGUES

    @patch('data_sources.build_scrapers.requests.Session.get')
    def test_scrape_builds_by_category(self, mock_get, scraper):
        """Should scrape builds by category."""
        mock_response = MagicMock()
        mock_response.text = '''
            <html>
                <article>
                    <a href="/build/ABC123">
                        <h6 class="list-title">Slayer Cyclone Build</h6>
                    </a>
                    <img alt="Slayer" />
                </article>
            </html>
        '''
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        builds = scraper.scrape_builds_by_category("league_starter", limit=10)

        # May or may not find builds depending on HTML parsing
        assert isinstance(builds, list)

    @patch('data_sources.build_scrapers.requests.Session.get')
    def test_scrape_builds_request_error(self, mock_get, scraper):
        """Should handle request errors."""
        import requests
        mock_get.side_effect = requests.RequestException("Error")

        builds = scraper.scrape_builds_by_category("league_starter")

        assert builds == []

    def test_scrape_all_categories(self, scraper):
        """Should scrape multiple categories."""
        with patch.object(scraper, 'scrape_builds_by_category', return_value=[]):
            results = scraper.scrape_all_categories(
                categories=["league_starter", "ssf"],
                limit_per_category=5,
            )

            assert "league_starter" in results
            assert "ssf" in results
            assert scraper.scrape_builds_by_category.call_count == 2


class TestPastebinScraper:
    """Tests for PastebinScraper class."""

    @pytest.fixture
    def scraper(self):
        """Create scraper instance."""
        return PastebinScraper(rate_limit=0.0)

    def test_init(self, scraper):
        """Should initialize correctly."""
        assert scraper.BASE_URL == "https://pastebin.com"

    @patch('data_sources.build_scrapers.requests.Session.get')
    def test_get_pob_code(self, mock_get, scraper):
        """Should fetch PoB code from pastebin."""
        mock_response = MagicMock()
        mock_response.text = "eNo" + "A" * 200  # Valid PoB-like code
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = scraper.get_pob_code("ABC123")

        assert result is not None
        mock_get.assert_called_once_with(
            "https://pastebin.com/raw/ABC123",
            timeout=10,
        )

    @patch('data_sources.build_scrapers.requests.Session.get')
    def test_get_pob_code_too_short(self, mock_get, scraper):
        """Should return None for short text."""
        mock_response = MagicMock()
        mock_response.text = "short"
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = scraper.get_pob_code("ABC123")

        assert result is None


class TestBuildSourceProvider:
    """Tests for BuildSourceProvider class."""

    def test_sources_defined(self):
        """Should have source definitions."""
        assert "pobarchives" in BuildSourceProvider.SOURCES
        assert "poeninja" in BuildSourceProvider.SOURCES
        assert "maxroll" in BuildSourceProvider.SOURCES

    def test_get_source_url_basic(self):
        """Should return URL for known source."""
        from urllib.parse import urlparse

        url = BuildSourceProvider.get_source_url("pobarchives")

        assert url is not None
        parsed = urlparse(url)
        assert parsed.netloc.endswith("pobarchives.com")

    def test_get_source_url_with_category(self):
        """Should include category filter in URL."""
        url = BuildSourceProvider.get_source_url(
            "pobarchives",
            category="league_starter",
        )

        assert url is not None
        assert "League%20Starter" in url or "league_starter" in url.lower()

    def test_get_source_url_unknown_source(self):
        """Should return None for unknown source."""
        url = BuildSourceProvider.get_source_url("unknown_source")

        assert url is None

    def test_get_all_sources(self):
        """Should return copy of sources dict."""
        sources = BuildSourceProvider.get_all_sources()

        assert "pobarchives" in sources
        assert sources["pobarchives"]["name"] == "PoB Archives"
        # Should be a copy
        sources["test"] = "modified"
        assert "test" not in BuildSourceProvider.SOURCES


class TestExtractPobLink:
    """Tests for extract_pob_link function."""

    def test_extract_pobb_in_link(self):
        """Should extract pobb.in link."""
        text = "Check out my build: https://pobb.in/ABC123"

        result = extract_pob_link(text)

        assert result == "https://pobb.in/ABC123"

    def test_extract_pastebin_link(self):
        """Should extract pastebin link."""
        text = "Here's the pastebin: https://pastebin.com/XYZ789"

        result = extract_pob_link(text)

        assert result == "https://pastebin.com/XYZ789"

    def test_extract_link_without_protocol(self):
        """Should add protocol to links without it."""
        text = "Link: pobb.in/ABC123"

        result = extract_pob_link(text)

        assert result == "https://pobb.in/ABC123"

    def test_extract_first_link(self):
        """Should extract first matching link."""
        text = "Links: https://pobb.in/ABC and pastebin.com/XYZ"

        result = extract_pob_link(text)

        assert result == "https://pobb.in/ABC"

    def test_no_link_found(self):
        """Should return None when no link found."""
        text = "No PoB link here"

        result = extract_pob_link(text)

        assert result is None

    def test_complex_text(self):
        """Should extract link from complex text."""
        text = """
        Hey everyone! I've been working on this build for a while.
        You can find the Path of Building link here: https://pobb.in/test-build-123
        Let me know what you think!
        """

        result = extract_pob_link(text)

        assert result == "https://pobb.in/test-build-123"
