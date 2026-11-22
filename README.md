# CineSuggest AI — Smart Movie Discovery & Recommendation Platform

CineSuggest AI is a clean, modern movie-discovery web platform with dedicated `backend/` and `frontend/` folders. It features rich movie catalog browsing from MongoDB, live Wikipedia metadata and poster scraping, YouTube trailer links, client-side personal Watchlists, and OpenRouter AI recommendations & spoiler-free summaries.

---

## 📁 Project Structure

```text
cinesuggeset/
├── backend/                  # Python backend application & logic
│   ├── app.py                # Flask routes and API endpoints
│   ├── config.py             # Configuration and environment loader
│   ├── database.py           # MongoDB connection and indexing
│   ├── seed_database.py      # Starter movie data seeder
│   ├── services/             # Core business logic
│   │   ├── movie_scraper.py  # Wikipedia API & parser
│   │   ├── movie_service.py  # Database query and caching service
│   │   ├── recommendation_service.py # OpenRouter recommendation engine
│   │   └── summary_service.py # AI spoiler-free summary generator
│   └── utils/
│       ├── serializers.py    # BSON / ObjectId serializer
│       └── validators.py     # Request input validation
├── frontend/                 # Frontend templates & static assets
│   ├── static/
│   │   ├── css/style.css     # Modern dark cinematic design system
│   │   ├── js/app.js         # Reactive UI, watchlist & API controller
│   │   └── images/           # Placeholder SVGs
│   └── templates/
│       └── index.html        # Single-page interface
├── requirements.txt          # Python dependencies
├── Procfile                  # Cloud deployment command
├── Dockerfile                # Docker build configuration
├── .dockerignore             # Docker build exclusions
├── .gitignore                # Git exclusions
├── .env                      # Local environment variables
├── .env.example              # Environment variables template
├── README.md                 # Project documentation
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

3. Run the backend server:
   ```powershell
   python backend\app.py
   ```

4. Open your browser and navigate to:
   ```
   http://127.0.0.1:5000
   ```
