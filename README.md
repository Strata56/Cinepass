# CineSuggest AI — Smart Movie Discovery & Recommendation Platform

CineSuggest AI is a unified, single-folder movie-discovery web platform. It features rich movie catalog browsing from MongoDB, live Wikipedia metadata and poster scraping for any missing movie, interactive YouTube trailer links, client-side personal Watchlists, and AI-powered recommendations & spoiler-free summaries via OpenRouter.

---

## 📁 Single-Folder Project Structure

All application files are consolidated directly into one clean folder:

```text
cinesuggeset/
├── app.py                    # Flask application routes
├── config.py                 # Configuration and environment loader
├── database.py               # MongoDB connection and indexing
├── seed_database.py          # Curated starter movies with Wikipedia posters
├── requirements.txt          # Python dependencies
├── .env                      # API keys and configuration
├── .env.example              # Environment variables template
├── services/
│   ├── movie_scraper.py      # Wikipedia API & Infobox parser
│   ├── movie_service.py      # Movie query, caching, and serialization
│   ├── recommendation_service.py # OpenRouter AI movie curator
│   └── summary_service.py    # Spoiler-free AI summary generator
├── static/
│   ├── css/style.css         # Modern dark cinematic design system
│   ├── js/app.js             # Reactive UI, watchlist, modal, and API controller
│   └── images/               # SVG fallback posters
├── templates/
│   └── index.html            # Single-page interface
└── venv/                     # Python virtual environment
```

---

## 🚀 How to Run

1. Open PowerShell or Command Prompt in the project folder:
   ```powershell
   cd C:\Users\HP\Downloads\ezyZip\cinesuggeset
   ```

2. Activate the virtual environment:
   ```powershell
   .\venv\Scripts\activate
   ```

3. Run the application:
   ```powershell
   python app.py
   ```

4. Open your browser and go to:
   ```
   http://127.0.0.1:5000
   ```
