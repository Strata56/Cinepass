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


def validate_recommendation_input(payload: dict[str, Any]) -> dict[str, str]:
    mood = clean_text(payload.get("mood"), 30)
    genre = clean_text(payload.get("genre"), 60)
    language = clean_text(payload.get("language"), 60)
    request = clean_text(payload.get("request"), 500)
    if mood.casefold() not in MOODS:
        raise ValidationError("Choose a mood for recommendations.")
    if not any((genre, language, request)):
        raise ValidationError("Add a genre, language, or a short request.")
    return {"mood": mood, "genre": genre or "Any", "language": language or "Any", "request": request or "None"}


def validate_summary_input(payload: dict[str, Any]) -> tuple[str, bool]:
    movie_id = clean_text(payload.get("movie_id"), 40)
    if not ObjectId.is_valid(movie_id):
        raise ValidationError("This movie could not be identified.")
    return movie_id, bool(payload.get("regenerate", False))
