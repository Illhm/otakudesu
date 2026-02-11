# Python Anime Search & Streaming Platform

This project turns the supplied request/response export into a runnable Python web platform.

## Features
- Home page with featured anime and latest episode updates.
- On-going anime listing with status badges.
- Full anime catalog with sorting and genre filtering.
- Search by title, synopsis, status, and genre metadata.
- Genre browser and per-genre listing pages.
- Next episode schedule page.
- Episode streaming page with quality options (360p/480p/720p) and embedded playback.
- `/api/debug` endpoint for inspecting normalized catalog data.

## Run
```bash
python main.py
```
Then open `http://localhost:8000`.

## Tests
```bash
python -m pytest tests/test_repository.py
```
