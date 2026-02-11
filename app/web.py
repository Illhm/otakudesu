from __future__ import annotations

import html
import json
from pathlib import Path
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

from app.repository import AnimeRepository

ROOT = Path(__file__).resolve().parents[1]
REPO = AnimeRepository(ROOT)


def page_layout(title: str, body: str) -> bytes:
    nav = (
        '<nav><a href="/">Home</a> | <a href="/ongoing">On-Going</a> | '
        '<a href="/anime">Anime List</a> | <a href="/genres">Genres</a> | '
        '<a href="/schedule">Next Episodes</a> | <a href="/search">Search</a></nav>'
    )
    style = """
    <style>
      body{font-family:Arial,sans-serif;max-width:1100px;margin:0 auto;padding:20px;background:#111;color:#eee}
      a{color:#7fd4ff;text-decoration:none} a:hover{text-decoration:underline}
      .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}
      .card{background:#1c1c1c;border:1px solid #2c2c2c;border-radius:10px;padding:12px}
      .badge{display:inline-block;padding:2px 8px;border-radius:999px;background:#244f74;font-size:12px}
      input,select{padding:8px;border-radius:6px;border:1px solid #444;background:#222;color:#fff}
      iframe{width:100%;height:460px;border:0;border-radius:8px;background:#000}
    </style>
    """
    doc = f"<!doctype html><html><head><meta charset='utf-8'><title>{html.escape(title)}</title>{style}</head><body><h1>{html.escape(title)}</h1>{nav}<hr>{body}</body></html>"
    return doc.encode("utf-8")


def json_response(start_response, payload: dict, status="200 OK"):
    body = json.dumps(payload, indent=2).encode("utf-8")
    start_response(status, [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(body)))])
    return [body]


def app(environ, start_response):
    path = environ.get("PATH_INFO", "/")
    query = parse_qs(environ.get("QUERY_STRING", ""))

    if path == "/":
        featured = REPO.featured()
        latest = REPO.latest_updates()
        body = ["<h2>Featured Anime</h2><div class='grid'>"]
        for anime in featured:
            body.append(f"<div class='card'><a href='/anime/{anime.slug}'><b>{html.escape(anime.title)}</b></a><br><span class='badge'>{html.escape(anime.status)}</span></div>")
        body.append("</div><h2>Latest Updates</h2><ul>")
        for ep in latest:
            body.append(f"<li><a href='/episode/{ep.slug}'>{html.escape(ep.title)}</a></li>")
        body.append("</ul>")
        payload = page_layout("Anime Streaming Platform", "".join(body))
    elif path == "/ongoing":
        cards = []
        for anime in REPO.ongoing():
            cards.append(f"<div class='card'><a href='/anime/{anime.slug}'>{html.escape(anime.title)}</a><br><span class='badge'>On-Going</span></div>")
        payload = page_layout("On-Going Anime", f"<div class='grid'>{''.join(cards)}</div>")
    elif path == "/anime":
        sort = query.get("sort", ["title"])[0]
        genre = query.get("genre", [""])[0] or None
        anime_list = REPO.anime_list(sort=sort, genre=genre)
        options = "".join(f"<option value='{g}' {'selected' if genre==g else ''}>{g}</option>" for g in REPO.genres())
        form = f"<form><label>Sort:</label><select name='sort'><option value='title'>Title</option><option value='status' {'selected' if sort=='status' else ''}>Status</option></select> <label>Genre:</label><select name='genre'><option value=''>All</option>{options}</select> <button type='submit'>Apply</button></form>"
        cards = [f"<div class='card'><a href='/anime/{a.slug}'>{html.escape(a.title)}</a><br>{html.escape(a.status)}</div>" for a in anime_list]
        payload = page_layout("Anime List", form + f"<p>Total: {len(anime_list)}</p><div class='grid'>{''.join(cards)}</div>")
    elif path.startswith("/anime/"):
        slug = path.split("/", 2)[2].strip("/")
        anime = REPO.find_anime(slug)
        if not anime:
            payload = page_layout("Not Found", "<p>Anime not found.</p>")
        else:
            eps = REPO.episodes_for_anime(slug)
            episodes_html = "".join(f"<li><a href='/episode/{ep.slug}'>{html.escape(ep.title)}</a></li>" for ep in eps) or "<li>No episode snapshot available.</li>"
            body = f"<p>{html.escape(anime.synopsis)}</p><p>Status: <span class='badge'>{html.escape(anime.status)}</span></p><p>Genres: {', '.join(anime.genres) or '-'}</p><h3>Episodes</h3><ul>{episodes_html}</ul>"
            payload = page_layout(anime.title, body)
    elif path.startswith("/episode/"):
        slug = path.split("/", 2)[2].strip("/")
        ep = REPO.find_episode(slug)
        if not ep:
            payload = page_layout("Not Found", "<p>Episode not found.</p>")
        else:
            chosen = query.get("quality", [""])[0] or (ep.streams[0].quality if ep.streams else "")
            options = "".join(
                f"<a href='/episode/{ep.slug}?quality={s.quality}' class='badge'>{s.quality} - {html.escape(s.provider)}</a> "
                for s in ep.streams
            )
            stream = next((s for s in ep.streams if s.quality == chosen), ep.streams[0] if ep.streams else None)
            player = f"<iframe src='{html.escape(stream.url)}' allowfullscreen></iframe>" if stream else "<p>No stream link available.</p>"
            payload = page_layout(ep.title, f"<p>{html.escape(ep.description)}</p><p>{options}</p>{player}")
    elif path == "/search":
        q = query.get("q", [""])[0]
        genre = query.get("genre", [""])[0] or None
        result = REPO.search(q, genre=genre)
        genre_options = "".join(f"<option value='{g}' {'selected' if g == genre else ''}>{g}</option>" for g in REPO.genres())
        form = f"<form><input name='q' value='{html.escape(q)}' placeholder='Search title, genre, status...'/> <select name='genre'><option value=''>All genres</option>{genre_options}</select> <button>Search</button></form>"
        rows = "".join(f"<li><a href='/anime/{a.slug}'>{html.escape(a.title)}</a> - {html.escape(a.status)}</li>" for a in result)
        payload = page_layout("Search Anime", form + f"<p>{len(result)} result(s)</p><ul>{rows}</ul>")
    elif path == "/genres":
        items = "".join(f"<li><a href='/genres/{g}'>{g}</a> ({len(v)} anime)</li>" for g, v in REPO.genres().items())
        payload = page_layout("Genre Filtering", f"<ul>{items}</ul>")
    elif path.startswith("/genres/"):
        genre = path.split("/", 2)[2].strip("/")
        anime = REPO.anime_list(genre=genre)
        cards = "".join(f"<li><a href='/anime/{a.slug}'>{html.escape(a.title)}</a></li>" for a in anime)
        payload = page_layout(f"Genre: {genre}", f"<p>{len(anime)} anime found.</p><ul>{cards}</ul>")
    elif path == "/schedule":
        rows = "".join(
            f"<tr><td>{html.escape(item.day)}</td><td><a href='/anime/{item.anime_slug}'>{html.escape(item.anime_title)}</a></td><td>{html.escape(item.next_episode)}</td></tr>"
            for item in REPO.next_schedule()
        )
        payload = page_layout("Next Anime Episode Schedule", f"<table><tr><th>Day</th><th>Anime</th><th>Status</th></tr>{rows}</table>")
    elif path == "/api/debug":
        return json_response(start_response, REPO.as_debug_dict())
    else:
        start_response("404 NOT FOUND", [("Content-Type", "text/plain")])
        return [b"Not found"]

    start_response("200 OK", [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(payload)))])
    return [payload]


def run(host: str = "0.0.0.0", port: int = 8000):
    with make_server(host, port, app) as server:
        print(f"Server running on http://{host}:{port}")
        server.serve_forever()


if __name__ == "__main__":
    run()
