# CineSuggest AI

CineSuggest AI is a simple, responsive movie-discovery website. It shows movies stored in MongoDB, searches Wikipedia when a movie is missing, and adds optional AI recommendations and spoiler-free summaries.

## Features

- Movie cards loaded from MongoDB with a resilient poster placeholder
- Movie search with MongoDB caching and public Wikipedia scraping
- Details modal for cast, director, duration, rating, description, and source
- Client-side genre, language, and rating filters
- Mood and natural-language movie recommendations through OpenRouter
- Spoiler-free AI summaries through Gemini or OpenAI
- Friendly messages when MongoDB or an AI provider is unavailable
- Responsive one-page dark movie interface

## Technology

- Flask and Python
- MongoDB with PyMongo
- HTML, CSS, and vanilla JavaScript
- Requests and BeautifulSoup for Wikipedia parsing
- OpenRouter for recommendations
- Gemini or OpenAI for summaries

## Project structure

```text
cinesuggeset/
├── app.py                    # Flask routes and API responses
├── config.py                 # Environment-based settings
├── database.py               # Shared MongoDB client
├── seed_database.py          # Sample movie data
├── services/                 # Movie, scraper, recommendation, summary logic
├── utils/                    # Validation and serialization helpers
├── templates/index.html      # Single-page interface
└── static/                   # CSS, JavaScript, and image placeholder
```

## Prerequisites

- Python 3.10 or newer
- MongoDB Community Server, or a MongoDB Atlas cluster
- An OpenRouter key for AI recommendations (optional)
- A Gemini key or an OpenAI key for AI summaries (optional; choose one provider)

## Install and run on Windows

```powershell
cd C:\yash\projects\cinesuggeset
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
```

If a `.env` already exists, do not overwrite it. Add the missing settings from `.env.example` to it instead.

Start MongoDB locally, then seed the database:

```powershell
python seed_database.py
python app.py
```

Open <http://127.0.0.1:5000>.

On macOS or Linux, activate the environment with:

```bash
source venv/bin/activate
```

## Environment variables

Copy `.env.example` to `.env` and set the variables you need. Never commit `.env`.

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | A long random Flask secret for local use. |
| `MONGODB_URI` | Local URI such as `mongodb://localhost:27017/`, or your Atlas URI. |
| `MONGODB_DATABASE` | Database name; defaults to `cinesuggest_ai`. |
| `OPENROUTER_API_KEY` / `OPENROUTER_MODEL` | Enables AI recommendations. |
| `SUMMARY_OPENROUTER_MODEL` | Structured-output model used when summaries run through OpenRouter. |
| `SUMMARY_PROVIDER` | Set to `gemini`, `openai`, or `openrouter`. |
| `GEMINI_API_KEY` / `GEMINI_MODEL` | Required only when `SUMMARY_PROVIDER=gemini`. |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | Required only when `SUMMARY_PROVIDER=openai`. |

`SUMMARY_PROVIDER=openrouter` reuses the OpenRouter key and model configured for recommendations. This is useful when the direct OpenAI project has no API quota.

Example provider choice:

```env
SUMMARY_PROVIDER=openai
OPENAI_MODEL=your-selected-openai-model
```

The included app continues to work without AI keys; only recommendations and summaries show a configuration message. All AI requests are sent by Flask, never browser JavaScript.

## MongoDB Atlas setup

1. Create a free MongoDB Atlas cluster.
2. Create a database user with a secure password.
3. Add your development IP address to the network access list.
4. Copy the Python connection string from Atlas.
5. Set `MONGODB_URI` in `.env`, and install `certifi` if your environment requires it for Atlas TLS.

## API routes

| Route | Purpose |
|---|---|
| `GET /api/movies?limit=20` | Returns stored movies. |
| `POST /api/search` | Looks up a title, then scrapes and caches it if needed. |
| `POST /api/recommend` | Requests three OpenRouter recommendations. |
| `POST /api/summary` | Returns a cached or newly generated AI summary. |

## Add a movie manually

Open `seed_database.py` and add a tuple to the `MOVIES` list. The fields are:

```text
(title, year, genres, language, duration, director, cast, description, rating, poster_url, source_url)
```

The last two fields are optional. Example:

```python
(
    "Movie Title",
    "2024",
    ["Drama", "Comedy"],
    "Hindi",
    "135 minutes",
    "Director Name",
    ["Actor One", "Actor Two"],
    "A short spoiler-free description.",
    8.0,
    "https://upload.wikimedia.org/path/to/poster.jpg",
    "https://en.wikipedia.org/wiki/Movie_Title",
),
```

Then run:

```powershell
venv\Scripts\python.exe seed_database.py
```

The unique normalized title prevents duplicates. If `poster_url` is blank, the seed script attempts to obtain the movie's Wikipedia infobox poster. You can also add the same document in MongoDB Compass under database `cinesuggest_ai`, collection `movies`; make sure `normalized_title` is lowercase and unique.

To fill every still-empty poster field with the built-in local artwork fallback, run:

```powershell
venv\Scripts\python.exe seed_database.py --fallback-only
```

## Limitations and security

- Wikipedia pages can change structure, so some scraped fields may be unavailable.
- AI outputs are validated but should be treated as recommendations, not authoritative movie data.
- The application does not include accounts, booking, payments, reviews, or ticketing.
- Keep API keys in `.env` only. Do not place them in HTML, CSS, JavaScript, commits, screenshots, or logs.
