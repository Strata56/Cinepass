from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from pymongo.errors import DuplicateKeyError, PyMongoError

from database import DatabaseUnavailable, get_movies_collection
from services.movie_scraper import normalize_movie_data, scrape_movie
from utils.serializers import serialize_movie
from utils.validators import normalize_movie_title


def _now() -> datetime:
    return datetime.now(timezone.utc)


def list_movies(limit: int) -> list[dict]:
    try:
        return [serialize_movie(normalize_movie_data(movie)) for movie in get_movies_collection().find().sort("updated_at", -1).limit(limit)]
    except PyMongoError as exc:
        raise DatabaseUnavailable("The movie database is currently unavailable.") from exc


def get_movie(movie_id: str) -> dict | None:
    try:
        movie = get_movies_collection().find_one({"_id": ObjectId(movie_id)})
        return serialize_movie(normalize_movie_data(movie)) if movie else None
    except PyMongoError as exc:
        raise DatabaseUnavailable("The movie database is currently unavailable.") from exc


def search_or_scrape_movie(query: str, timeout: int) -> tuple[dict | None, str]:
    normalized = normalize_movie_title(query)
    try:
        collection = get_movies_collection()
        existing = collection.find_one({"normalized_title": normalized})
        if existing:
            return serialize_movie(normalize_movie_data(existing)), "database"
    except PyMongoError as exc:
        raise DatabaseUnavailable("The movie database is currently unavailable.") from exc

    scraped = normalize_movie_data(scrape_movie(query, timeout) or {})
    if not scraped or not scraped.get("title"):
        return None, "scraped"
    scraped.update({
        "normalized_title": normalized,
        "ai_summary": None,
        "summary_genre": None,
        "summary_mood": None,
        "summary_suitable_for": None,
        "summary_provider": None,
        "created_at": _now(),
        "updated_at": _now(),
    })
    try:
        result = collection.update_one({"normalized_title": normalized}, {"$setOnInsert": scraped}, upsert=True)
        if result.upserted_id:
            scraped["_id"] = result.upserted_id
            return serialize_movie(normalize_movie_data(scraped)), "scraped"
        existing = collection.find_one({"normalized_title": normalized})
        return serialize_movie(normalize_movie_data(existing)), "database"
    except DuplicateKeyError:
        existing = collection.find_one({"normalized_title": normalized})
        return serialize_movie(normalize_movie_data(existing)), "database"
    except PyMongoError as exc:
        raise DatabaseUnavailable("The movie database is currently unavailable.") from exc


def save_summary(movie_id: str, summary: dict[str, str], provider: str) -> None:
    try:
        get_movies_collection().update_one(
            {"_id": ObjectId(movie_id)},
            {"$set": {
                "ai_summary": summary["summary"],
                "summary_genre": summary["genre"],
                "summary_mood": summary["mood"],
                "summary_suitable_for": summary["suitable_for"],
                "summary_provider": provider,
                "updated_at": _now(),
            }},
        )
    except PyMongoError as exc:
        raise DatabaseUnavailable("The movie database is currently unavailable.") from exc
