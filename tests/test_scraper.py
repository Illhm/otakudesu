import pytest
import os
import sys

# Add src to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from scraper import OtakudesuScraper

@pytest.fixture
def scraper():
    return OtakudesuScraper()

def test_find_local_file(scraper):
    """Test finding a local file for a known URL."""
    # This URL should exist in the index.csv
    url = "https://otakudesu.best/"
    filepath = scraper._find_local_file(url)
    assert filepath is not None
    assert "04_res_body.html" in filepath
    assert os.path.exists(filepath)

def test_get_home_page(scraper):
    """Test fetching the home page content."""
    data = scraper.get_home()
    assert isinstance(data, dict)
    assert "ongoing" in data
    assert len(data['ongoing']) > 0

def test_get_ongoing_anime(scraper):
    """Test fetching ongoing anime."""
    ongoing = scraper.get_ongoing_anime(page=1)
    assert isinstance(ongoing, list)
    assert len(ongoing) > 0

def test_get_anime_details(scraper):
    """Test fetching anime details."""
    # Use a known slug from the dataset
    slug = "shibou-yuugi-meshi-kuu-sub-indo"
    details = scraper.get_anime_details(slug)
    assert details is not None
    assert details['title'] is not None
    assert isinstance(details['episodes'], list)

def test_get_episode_details(scraper):
    """Test fetching episode details."""
    # I need a valid episode slug.
    # Use Oshi no Ko S3 which we know has episodes in the index
    ep_slug = "onk-s3-episode-1-sub-indo"
    ep_details = scraper.get_episode_details(ep_slug)
    assert ep_details is not None
    assert ep_details['title'] is not None
    assert 'mirrors' in ep_details
