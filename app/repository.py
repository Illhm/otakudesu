from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from app.models import Anime, Catalog, Episode, ScheduleItem
from app.parser import parse_catalog


class AnimeRepository:
    def __init__(self, root: Path):
        self.root = root
        self.catalog: Catalog = parse_catalog(root)

    def featured(self, limit: int = 8) -> list[Anime]:
        slugs = self.catalog.featured[:limit]
        return [self.catalog.anime[s] for s in slugs if s in self.catalog.anime]

    def latest_updates(self, limit: int = 12) -> list[Episode]:
        episodes = sorted(self.catalog.episodes.values(), key=lambda ep: ep.slug, reverse=True)
        return episodes[:limit]

    def ongoing(self) -> list[Anime]:
        return sorted((a for a in self.catalog.anime.values() if "on" in a.status.lower()), key=lambda x: x.title)

    def anime_list(self, sort: str = "title", genre: str | None = None) -> list[Anime]:
        anime = list(self.catalog.anime.values())
        if genre:
            allowed = set(self.catalog.genres.get(genre, []))
            anime = [item for item in anime if item.slug in allowed or genre in item.genres]

        if sort == "status":
            anime.sort(key=lambda x: (x.status, x.title))
        else:
            anime.sort(key=lambda x: x.title)
        return anime

    def genres(self) -> dict[str, list[str]]:
        return dict(sorted(self.catalog.genres.items()))

    def next_schedule(self, limit: int = 20) -> list[ScheduleItem]:
        return self.catalog.schedule[:limit]

    def find_anime(self, slug: str) -> Anime | None:
        return self.catalog.anime.get(slug)

    def find_episode(self, slug: str) -> Episode | None:
        return self.catalog.episodes.get(slug)

    def episodes_for_anime(self, anime_slug: str) -> list[Episode]:
        eps = [ep for ep in self.catalog.episodes.values() if ep.anime_slug == anime_slug]
        return sorted(eps, key=lambda ep: ep.slug)

    def search(self, query: str = "", genre: str | None = None) -> list[Anime]:
        query = query.lower().strip()
        anime = self.anime_list(genre=genre)
        if not query:
            return anime

        result = []
        for item in anime:
            haystack = " ".join([item.title, item.synopsis, item.status, " ".join(item.genres)]).lower()
            if query in haystack:
                result.append(item)
        return result

    def as_debug_dict(self) -> dict:
        return {
            "anime": {k: asdict(v) for k, v in self.catalog.anime.items()},
            "episodes": {k: asdict(v) for k, v in self.catalog.episodes.items()},
            "genres": self.catalog.genres,
            "schedule": [asdict(i) for i in self.catalog.schedule],
        }
