from pathlib import Path

from app.repository import AnimeRepository


def test_catalog_has_anime_entries():
    repo = AnimeRepository(Path(__file__).resolve().parents[1])
    assert len(repo.catalog.anime) > 10


def test_search_and_streams_available():
    repo = AnimeRepository(Path(__file__).resolve().parents[1])
    results = repo.search("oshi")
    assert results
    episodes = repo.latest_updates()
    assert any(ep.streams for ep in episodes)
