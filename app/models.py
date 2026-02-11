from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(slots=True)
class StreamSource:
    quality: str
    provider: str
    url: str


@dataclass(slots=True)
class Episode:
    slug: str
    title: str
    anime_slug: str
    description: str = ""
    streams: List[StreamSource] = field(default_factory=list)


@dataclass(slots=True)
class Anime:
    slug: str
    title: str
    synopsis: str = ""
    status: str = "Unknown"
    genres: List[str] = field(default_factory=list)
    latest_episode: str = ""


@dataclass(slots=True)
class ScheduleItem:
    day: str
    anime_title: str
    anime_slug: str
    next_episode: str = "TBA"


@dataclass(slots=True)
class Catalog:
    anime: Dict[str, Anime] = field(default_factory=dict)
    episodes: Dict[str, Episode] = field(default_factory=dict)
    genres: Dict[str, List[str]] = field(default_factory=dict)
    schedule: List[ScheduleItem] = field(default_factory=list)
    featured: List[str] = field(default_factory=list)
