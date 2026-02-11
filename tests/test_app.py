import pytest
import os
import sys

# Add src to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_home_page(client):
    """Test the home page."""
    rv = client.get('/')
    assert rv.status_code == 200
    # Check for some text that should be on the home page
    assert b"AnimeStream" in rv.data or b"Ongoing" in rv.data

def test_ongoing_page(client):
    """Test the ongoing anime page."""
    rv = client.get('/ongoing')
    assert rv.status_code == 200
    assert b"Ongoing Anime" in rv.data

def test_anime_list_page(client):
    """Test the anime list page."""
    rv = client.get('/list')
    assert rv.status_code == 200
    assert b"Anime List" in rv.data

def test_search_page(client):
    """Test the search page."""
    rv = client.get('/search?q=test')
    assert rv.status_code == 200
    assert b"Search Results" in rv.data
