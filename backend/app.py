from __future__ import annotations

import sys
from pathlib import Path

# Ensure backend directory is in python search path
_backend_path = str(Path(__file__).resolve().parent)
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

from flask import Flask, jsonify, render_template, request

from config import Config
from database import DatabaseUnavailable, initialize_database, get_movies_collection
from services.movie_scraper import ScraperError
from services.movie_service import get_movie, list_movies, save_summary, search_or_scrape_movie
from services.recommendation_service import RecommendationError, get_recommendations
from services.summary_service import SummaryError, generate_summary
from utils.validators import ValidationError, validate_movie_query, validate_recommendation_input, validate_summary_input


def error(message: str, status: int = 400):
    return jsonify({"success": False, "message": message}), status


def json_body() -> dict:
    if not request.is_json:
        raise ValidationError("Send a JSON request.")
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ValidationError("Send a valid JSON object.")
    return payload


def create_app() -> Flask:
    Config.validate()
    backend_dir = Path(__file__).resolve().parent
    root_dir = backend_dir.parent
    frontend_dir = root_dir / "frontend"

    template_dir = frontend_dir / "templates" if (frontend_dir / "templates").exists() else backend_dir / "templates"
    static_dir = frontend_dir / "static" if (frontend_dir / "static").exists() else backend_dir / "static"

    app = Flask(
        __name__,
        template_folder=str(template_dir),
        static_folder=str(static_dir),
    )
    app.config.from_object(Config)
    initialize_database(app)

    @app.get("/")
    def index():
        return render_template("index.html", app_name=app.config["APP_NAME"])

    @app.get("/api/movies")
    def movies():
        try:
            limit = max(1, min(int(request.args.get("limit", 100)), 200))
        except ValueError:
            limit = 100
        genre = request.args.get("genre", "").strip()
        language = request.args.get("language", "").strip()
        search_query = request.args.get("search", "").strip()
        sort_by = request.args.get("sort_by", "newest").strip()
        try:
            min_rating = float(request.args.get("min_rating", 0))
        except ValueError:
            min_rating = 0.0
        try:
            return jsonify({"success": True, "movies": list_movies(limit, genre=genre, language=language, min_rating=min_rating, search=search_query, sort_by=sort_by)})
        except DatabaseUnavailable:
            return error("The movie database is currently unavailable.", 503)

    @app.get("/api/stats")
    def stats():
        try:
            coll = get_movies_collection()
            count = coll.count_documents({})
            all_genres = coll.distinct("genres")
            flat_genres = set()
            for g in all_genres:
                if isinstance(g, list):
                    flat_genres.update(g)
                elif isinstance(g, str) and g and g != "Not available":
                    flat_genres.add(g)
            return jsonify({
                "success": True,
                "total_movies": count,
                "genres": sorted(g for g in flat_genres if g and g != "Not available"),
                "ai_enabled": bool(app.config.get("OPENROUTER_API_KEY")),
            })
        except DatabaseUnavailable:
            return error("The movie database is currently unavailable.", 503)

    @app.post("/api/search")
    def search():
        try:
            query = validate_movie_query(json_body().get("query"))
            movie, source = search_or_scrape_movie(query, app.config["REQUEST_TIMEOUT_SECONDS"])
            if not movie:
                return error("Movie information could not be found.", 404)
            return jsonify({"success": True, "movie": movie, "source": source})
        except ValidationError as exc:
            return error(str(exc))
        except DatabaseUnavailable:
            return error("The movie database is currently unavailable.", 503)
        except ScraperError:
            return error("Movie information could not be collected from the web.", 502)

    @app.post("/api/recommend")
    def recommend():
        try:
            preferences = validate_recommendation_input(json_body())
            return jsonify({"success": True, "recommendations": get_recommendations(preferences)})
        except ValidationError as exc:
            return error(str(exc))
        except RecommendationError as exc:
            return error(str(exc), 503)

    @app.post("/api/summary")
    def summary():
        try:
            movie_id, regenerate = validate_summary_input(json_body())
            movie = get_movie(movie_id)
            if not movie:
                return error("Movie information could not be found.", 404)
            if movie.get("ai_summary") and not regenerate:
                result = {
                    "title": movie["title"],
                    "summary": movie["ai_summary"],
                    "genre": movie.get("summary_genre") or "Not available",
                    "mood": movie.get("summary_mood") or "Not available",
                    "suitable_for": movie.get("summary_suitable_for") or "Not available",
                }
                return jsonify({"success": True, "result": result, "provider": movie.get("summary_provider"), "source": "database"})
            result, provider = generate_summary(movie)
            save_summary(movie_id, result, provider)
            return jsonify({"success": True, "result": result, "provider": provider, "source": "generated"})
        except ValidationError as exc:
            return error(str(exc))
        except DatabaseUnavailable:
            return error("The movie database is currently unavailable.", 503)
        except SummaryError as exc:
            return error(str(exc), 503)

    return app


app = create_app()


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=app.config["DEBUG"])
