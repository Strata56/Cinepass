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


def _get_fallback_movies() -> list[dict]:
    try:
        from seed_database import MOVIES, make_movie
        fallback = []
        for idx, m in enumerate(MOVIES, start=1):
            doc = make_movie(m)
            doc["id"] = f"seed_{idx}"
            doc["_id"] = doc["id"]
            fallback.append(normalize_movie_data(doc))
        return fallback
    except Exception as exc:
        print(f"[movie_service] Fallback load notice: {exc}", flush=True)
        return []


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

        result = [serialize_movie(normalize_movie_data(movie)) for movie in cursor.limit(limit)]
        if result:
            return result
    except Exception as exc:
        print(f"[movie_service] Database query notice: {exc}. Serving curated movies.", flush=True)

    # In-memory filtered fallback
    fallback = _get_fallback_movies()
    if genre:
        fallback = [m for m in fallback if any(genre.lower() == g.lower() for g in m.get("genres", []))]
    if language:
        fallback = [m for m in fallback if language.lower() in m.get("language", "").lower()]
    if min_rating > 0:
        fallback = [m for m in fallback if (m.get("rating") or 0) >= min_rating]
    if search:
        s = search.lower()
        fallback = [
            m for m in fallback
            if s in m.get("title", "").lower()
            or s in m.get("director", "").lower()
            or any(s in c.lower() for c in m.get("cast", []))
        ]

    if sort_by == "rating_desc":
        fallback.sort(key=lambda x: x.get("rating") or 0, reverse=True)
    elif sort_by == "year_desc":
        fallback.sort(key=lambda x: int(x.get("year") or 0) if str(x.get("year", "")).isdigit() else 0, reverse=True)
    elif sort_by == "title_asc":
        fallback.sort(key=lambda x: x.get("title", "").lower())

    return fallback[:limit]


def get_movie(movie_id: str) -> dict | None:
    try:
        if ObjectId.is_valid(movie_id):
            movie = get_movies_collection().find_one({"_id": ObjectId(movie_id)})
            if movie:
                return serialize_movie(normalize_movie_data(movie))
    except Exception as exc:
        print(f"[movie_service] DB notice on movie {movie_id}: {exc}", flush=True)

    for m in _get_fallback_movies():
        if str(m.get("id")) == str(movie_id) or str(m.get("_id")) == str(movie_id) or m.get("title", "").lower() == str(movie_id).lower():
            return m
    return None


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
    except Exception as exc:
        print(f"[movie_service] DB search notice: {exc}. Checking curated fallback.", flush=True)

    # Check curated library before scraping from the web
    for m in _get_fallback_movies():
        if m.get("normalized_title") == normalized or clean_query.lower() in m.get("title", "").lower():
            return m, "database"

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
        collection = get_movies_collection()
        result = collection.update_one({"normalized_title": normalized}, {"$setOnInsert": scraped}, upsert=True)
        if result.upserted_id:
            scraped["_id"] = result.upserted_id
            return serialize_movie(normalize_movie_data(scraped)), "scraped"
        existing = collection.find_one({"normalized_title": normalized})
        if existing:
            return serialize_movie(normalize_movie_data(existing)), "database"
        return serialize_movie(normalize_movie_data(scraped)), "scraped"
    except Exception:
        scraped["id"] = "scraped_" + re.sub(r"\W+", "_", scraped["title"])
        return scraped, "scraped"


def save_summary(movie_id: str, summary: dict[str, str], provider: str) -> None:
    try:
        if ObjectId.is_valid(movie_id):
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
    except Exception as exc:
        print(f"[movie_service] Notice: Could not cache summary to DB: {exc}", flush=True)
