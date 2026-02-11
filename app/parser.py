from __future__ import annotations

import html
import re
import zipfile
from pathlib import Path
from urllib.parse import urlparse

from app.models import Anime, Catalog, Episode, ScheduleItem, StreamSource

BASE_HOST = "otakudesu.best"
DAY_NAMES = [
    "Senin",
    "Selasa",
    "Rabu",
    "Kamis",
    "Jumat",
    "Sabtu",
    "Minggu",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def clean_text(value: str) -> str:
    value = html.unescape(re.sub(r"<[^>]+>", " ", value))
    return re.sub(r"\s+", " ", value).strip()


def extract_links(page: str):
    link_re = re.compile(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
    return [(href.strip(), clean_text(label)) for href, label in link_re.findall(page)]


def extract_title(page: str) -> str:
    m = re.search(r"<title>(.*?)</title>", page, re.I | re.S)
    return clean_text(m.group(1)) if m else ""


def extract_meta_desc(page: str) -> str:
    m = re.search(r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\'](.*?)["\']', page, re.I | re.S)
    return clean_text(m.group(1)) if m else ""


def slug_from_url(url: str) -> str:
    p = urlparse(url)
    return p.path.strip("/").split("/")[-1]




def ensure_dataset(root: Path) -> None:
    if (root / "otakudesu.best").exists():
        return
    archive = root / "reqres_readable (8).zip"
    if archive.exists():
        with zipfile.ZipFile(archive, "r") as zf:
            zf.extractall(root)

def parse_catalog(repo_root: Path) -> Catalog:
    ensure_dataset(repo_root)
    data = Catalog()
    html_files = sorted(repo_root.glob("otakudesu.best/*/04_res_body.html"))

    fallback_streams = _fallback_streams(repo_root)

    for file_path in html_files:
        page = file_path.read_text(encoding="utf-8", errors="ignore")
        req_name = file_path.parent.name

        if "GET_anime-list_" in req_name:
            _parse_anime_list(page, data)
        elif "GET_ongoing-anime_" in req_name:
            _parse_ongoing_page(page, data)
        elif "GET_genre-list_" in req_name:
            _parse_genre_index(page, data)
        elif "GET_jadwal-rilis_" in req_name:
            _parse_schedule(page, data)
        elif "GET_anime_" in req_name:
            _parse_anime_detail(page, data)
        elif "episode_" in req_name:
            _parse_episode(page, data, fallback_streams)
        elif "GET_genres_" in req_name:
            _parse_genre_page(page, data)
        elif req_name.endswith("GET_"):
            _parse_home(page, data)

    if not data.featured:
        data.featured = list(data.anime)[:8]
    return data


def _parse_anime_list(page: str, data: Catalog) -> None:
    for href, label in extract_links(page):
        if "/anime/" not in href:
            continue
        slug = slug_from_url(href)
        if not slug:
            continue
        anime = data.anime.setdefault(slug, Anime(slug=slug, title=label or slug.replace("-", " ").title()))
        if label:
            anime.title = label


def _parse_ongoing_page(page: str, data: Catalog) -> None:
    links = extract_links(page)
    for href, label in links:
        if "/anime/" in href:
            slug = slug_from_url(href)
            anime = data.anime.setdefault(slug, Anime(slug=slug, title=label or slug.replace("-", " ").title()))
            anime.status = "On-Going"
        if "/episode/" in href:
            e_slug = slug_from_url(href)
            anime_slug = e_slug.split("-episode-")[0].replace("onk-s3", "oshi-ko-s3-sub-indo")
            title = label or e_slug.replace("-", " ").title()
            data.episodes.setdefault(e_slug, Episode(slug=e_slug, title=title, anime_slug=anime_slug))


def _parse_genre_index(page: str, data: Catalog) -> None:
    for href, label in extract_links(page):
        if "/genres/" in href:
            genre_slug = slug_from_url(href)
            data.genres.setdefault(genre_slug, [])


def _parse_schedule(page: str, data: Catalog) -> None:
    chunks = re.findall(r"<(?:li|tr|div)[^>]*>(.*?)</(?:li|tr|div)>", page, re.I | re.S)
    for chunk in chunks:
        text = clean_text(chunk)
        if not text:
            continue
        day = next((d for d in DAY_NAMES if d.lower() in text.lower()), "")
        if not day:
            continue
        for href, label in extract_links(chunk):
            if "/anime/" not in href:
                continue
            slug = slug_from_url(href)
            data.anime.setdefault(slug, Anime(slug=slug, title=label or slug.replace("-", " ").title()))
            data.schedule.append(ScheduleItem(day=day, anime_title=label, anime_slug=slug, next_episode="Upcoming"))


def _parse_anime_detail(page: str, data: Catalog) -> None:
    title = extract_title(page).split("|")[0].strip()
    canonical = re.search(r'<meta[^>]+property=["\']og:url["\'][^>]+content=["\']([^"\']+)', page, re.I)
    if not canonical:
        return
    slug = slug_from_url(canonical.group(1))
    anime = data.anime.setdefault(slug, Anime(slug=slug, title=title or slug.replace("-", " ").title()))
    anime.title = anime.title or title
    anime.synopsis = extract_meta_desc(page)

    status_m = re.search(r"Status\s*</[^>]+>\s*:?\s*([^<]+)", page, re.I)
    if status_m:
        anime.status = clean_text(status_m.group(1))

    for href, label in extract_links(page):
        if "/genres/" in href:
            g = slug_from_url(href)
            if g not in anime.genres:
                anime.genres.append(g)
            data.genres.setdefault(g, [])
            if slug not in data.genres[g]:
                data.genres[g].append(slug)

        if "/episode/" in href:
            e_slug = slug_from_url(href)
            if e_slug not in data.episodes:
                data.episodes[e_slug] = Episode(slug=e_slug, title=label, anime_slug=slug)
            anime.latest_episode = label


def _parse_episode(page: str, data: Catalog, fallback_streams: list[StreamSource]) -> None:
    canonical = re.search(r'<meta[^>]+property=["\']og:url["\'][^>]+content=["\']([^"\']+)', page, re.I)
    title = extract_title(page).split("|")[0].strip()
    if not canonical:
        return
    slug = slug_from_url(canonical.group(1))
    anime_slug = slug.split("-episode-")[0].replace("onk-s3", "oshi-ko-s3-sub-indo")
    ep = data.episodes.setdefault(slug, Episode(slug=slug, title=title, anime_slug=anime_slug))
    ep.title = title
    ep.description = extract_meta_desc(page)

    found_streams: list[StreamSource] = []
    for href, label in extract_links(page):
        provider = label or urlparse(href).netloc
        if any(host in href for host in ["blogger.com", "filedon.co", "odvidhide.com", "mega.nz", "desustream.com"]):
            quality = "480p"
            if "720" in provider or "hq" in provider.lower():
                quality = "720p"
            elif "360" in provider:
                quality = "360p"
            found_streams.append(StreamSource(quality=quality, provider=provider, url=href))

    if not found_streams:
        found_streams = fallback_streams
    ep.streams = _dedupe_streams(found_streams)


def _parse_genre_page(page: str, data: Catalog) -> None:
    title = extract_title(page)
    g_slug_match = re.search(r"/genres/([^/]+)/", page)
    if not g_slug_match:
        return
    g_slug = g_slug_match.group(1)
    data.genres.setdefault(g_slug, [])
    for href, label in extract_links(page):
        if "/anime/" not in href:
            continue
        slug = slug_from_url(href)
        data.anime.setdefault(slug, Anime(slug=slug, title=label or slug.replace("-", " ").title()))
        if slug not in data.genres[g_slug]:
            data.genres[g_slug].append(slug)
    if title and not data.genres[g_slug]:
        data.genres[g_slug] = []


def _parse_home(page: str, data: Catalog) -> None:
    for href, _ in extract_links(page):
        if "/anime/" in href:
            slug = slug_from_url(href)
            if slug in data.anime and slug not in data.featured:
                data.featured.append(slug)


def _dedupe_streams(streams: list[StreamSource]) -> list[StreamSource]:
    seen = set()
    result = []
    for stream in streams:
        key = (stream.quality, stream.url)
        if key in seen:
            continue
        seen.add(key)
        result.append(stream)
    return result[:6]


def _fallback_streams(repo_root: Path) -> list[StreamSource]:
    sources = []
    candidates = [
        ("360p", "Filedon", repo_root / "filedon.co/00799_GET_embed_QvvubTKG5k/04_res_body.html"),
        ("480p", "ODVidHide #1", repo_root / "odvidhide.com/00824_GET_embed_yblec6u1eavr/04_res_body.html"),
        ("720p", "ODVidHide #2", repo_root / "odvidhide.com/00846_GET_embed_7vh4zo2k5378/04_res_body.html"),
    ]
    for quality, provider, file_path in candidates:
        if not file_path.exists():
            continue
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r'<iframe[^>]+src=["\']([^"\']+)', text, re.I)
        url = m.group(1) if m else ""
        if not url:
            # fallback to a provider landing URL
            url = f"https://{file_path.parts[0]}/"
        sources.append(StreamSource(quality=quality, provider=provider, url=url))
    return sources
