from __future__ import annotations

import re
from datetime import datetime, timezone

from bson import ObjectId
from pymongo.errors import DuplicateKeyError, PyMongoError

from database import DatabaseUnavailable, get_movies_collection
from services.movie_scraper import normalize_movie_data, scrape_movie
from utils.serializers import serialize_movie
from utils.validators import normalize_movie_title


def _now() -> datetime:
    return datetime.now(timezone.utc)


def list_movies(limit: int = 100, genre: str = "", language: str = "", min_rating: float = 0.0, search: str = "", sort_by: str = "newest") -> list[dict]:
    try:
        query_filter: dict = {}
        if genre:
            query_filter["genres"] = {"$regex": f"^{re.escape(genre)}$", "$options": "i"}
        if language:
            query_filter["language"] = {"$regex": re.escape(language), "$options": "i"}
        if min_rating > 0:
            query_filter["rating"] = {"$gte": min_rating}
        if search:
            query_filter["$or"] = [
                {"title": {"$regex": re.escape(search), "$options": "i"}},
                {"director": {"$regex": re.escape(search), "$options": "i"}},
                {"cast": {"$regex": re.escape(search), "$options": "i"}},
            ]

        cursor = get_movies_collection().find(query_filter)

        if sort_by == "rating_desc":
            cursor = cursor.sort("rating", -1)
        elif sort_by == "year_desc":
            cursor = cursor.sort("year", -1)
        elif sort_by == "title_asc":
            cursor = cursor.sort("title", 1)
        else:
            cursor = cursor.sort("updated_at", -1)

        return [serialize_movie(normalize_movie_data(movie)) for movie in cursor.limit(limit)]
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
    clean_query = query.strip()
    try:
        collection = get_movies_collection()
        # 1. Exact normalized match
        existing = collection.find_one({"normalized_title": normalized})
        if existing:
            return serialize_movie(normalize_movie_data(existing)), "database"
        # 2. Case-insensitive exact or partial match on title
        matched = collection.find_one({"title": {"$regex": f"^{re.escape(clean_query)}$", "$options": "i"}})
        if not matched:
            matched = collection.find_one({"title": {"$regex": re.escape(clean_query), "$options": "i"}})
        if matched:
            return serialize_movie(normalize_movie_data(matched)), "database"
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
