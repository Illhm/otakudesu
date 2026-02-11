import pytest
import os
import sys
from unittest.mock import MagicMock, patch

# Add src to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from scraper import OtakudesuScraper

@pytest.fixture
def scraper():
    return OtakudesuScraper()

def test_get_home_page(scraper):
    """Test fetching the home page content live."""
    data = scraper.get_home()
    assert isinstance(data, dict)
    assert "ongoing" in data
    # We expect some content usually, but empty list is valid if site changed structure or is empty
    assert len(data['ongoing']) > 0

def test_get_ongoing_anime(scraper):
    """Test fetching ongoing anime live."""
    ongoing = scraper.get_ongoing_anime(page=1)
    assert isinstance(ongoing, list)
    assert len(ongoing) > 0

def test_get_genre_list(scraper):
    """Test fetching genre list live (since it seems accessible)."""
    genres = scraper.get_genre_list()
    assert isinstance(genres, list)
    assert len(genres) > 0

def test_get_anime_details_mock(scraper):
    """Test fetching anime details with mocked response due to Cloudflare blocks on CI."""
    html_content = """
    <html>
        <div class="fotoanime"><img src="http://example.com/img.jpg"></div>
        <div class="infozingle">
            <p>Skor: 8.5</p>
            <p>Produser: Studio A</p>
        </div>
        <div class="sinopc">This is a synopsis.</div>
        <div class="jdlrx"><h1>Mock Anime Title</h1></div>
        <div class="episodelist">
            <li><a href="https://otakudesu.best/episode/mock-episode-1/">Episode 1</a><span class="zeebr">Today</span></li>
            <li><a href="https://otakudesu.best/episode/mock-episode-2/">Episode 2</a><span class="zeebr">Yesterday</span></li>
        </div>
    </html>
    """
    with patch('requests.Session.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = html_content.encode('utf-8')
        mock_get.return_value = mock_response

        details = scraper.get_anime_details("mock-anime")
        assert details is not None
        assert details['title'] == "Mock Anime Title"
        assert details['synopsis'] == "This is a synopsis."
        assert len(details['episodes']) == 2
        assert details['episodes'][0]['title'] == "Episode 1"
        assert details['episodes'][0]['slug'] == "mock-episode-1"

def test_get_episode_details_mock(scraper):
    """Test fetching episode details with mocked response due to Cloudflare blocks on CI."""
    html_content = """
    <html>
        <h1 class="posttl">Mock Episode Title</h1>
        <div class="prevnext">
            <div class="flir">
                <a href="https://otakudesu.best/episode/prev/">Prev</a>
                <a href="https://otakudesu.best/episode/next/">Next</a>
            </div>
        </div>
        <div class="mirrorstream">
            <ul class="m360p">
                <li><a href="#" data-content="mockdata1">Host1</a></li>
            </ul>
            <ul class="m720p">
                <li><a href="#" data-content="mockdata2">Host2</a></li>
            </ul>
        </div>
        <iframe src="https://desustream.com/embed"></iframe>
    </html>
    """
    with patch('requests.Session.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = html_content.encode('utf-8')
        mock_get.return_value = mock_response

        details = scraper.get_episode_details("mock-episode")
        assert details is not None
        assert details['title'] == "Mock Episode Title"
        assert details['prev_episode'] == "prev"
        assert details['next_episode'] == "next"
        assert '360p' in details['mirrors']
        assert details['mirrors']['360p'][0]['host'] == "Host1"
        assert details['default_stream'] == "https://desustream.com/embed"
