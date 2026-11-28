from __future__ import annotations

import re
from typing import Any

from bson import ObjectId


class ValidationError(ValueError):
    pass


MOODS = {"happy", "emotional", "romantic", "excited", "relaxed", "adventurous", "family"}


def clean_text(value: Any, maximum: int) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value).strip()[:maximum]


def normalize_movie_title(value: str) -> str:
    return clean_text(value, 100).casefold()


def validate_movie_query(value: Any) -> str:
    query = clean_text(value, 100)
    if not query:
        raise ValidationError("Enter a movie name to search.")
    if len(query) < 2:
        raise ValidationError("Enter at least two characters to search.")
    return query


def validate_recommendation_input(payload: dict[str, Any]) -> dict[str, Any]:
    selected_raw = payload.get("selected_movies", [])
    selected_movies: list[str] = []
    if isinstance(selected_raw, list):
        for item in selected_raw:
            val = clean_text(item, 100)
            if val and val not in selected_movies:
                selected_movies.append(val)
    elif isinstance(selected_raw, str) and selected_raw.strip():
        for item in selected_raw.split(","):
            val = clean_text(item, 100)
            if val and val not in selected_movies:
                selected_movies.append(val)
    selected_movies = selected_movies[:15]

    mood = clean_text(payload.get("mood"), 30)
    genre = clean_text(payload.get("genre"), 60)
    language = clean_text(payload.get("language"), 60)
    request = clean_text(payload.get("request"), 500)

    has_selection = len(selected_movies) > 0
    has_mood = mood.casefold() in MOODS
    has_custom = any((genre, language, request))

    if not has_selection and not has_mood and not has_custom:
        raise ValidationError("Select movies you like, choose a mood, or describe what you want to watch.")

    return {
        "selected_movies": selected_movies,
        "mood": mood if has_mood else "Balanced / Any",
        "genre": genre or "Any",
        "language": language or "Any",
        "request": request or "None",
    }


def validate_summary_input(payload: dict[str, Any]) -> tuple[str, bool]:
    movie_id = clean_text(payload.get("movie_id"), 40)
    if not ObjectId.is_valid(movie_id):
        raise ValidationError("This movie could not be identified.")
    return movie_id, bool(payload.get("regenerate", False))
