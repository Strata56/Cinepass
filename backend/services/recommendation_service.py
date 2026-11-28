from __future__ import annotations

import json
import re

from openai import OpenAI

from config import Config


class RecommendationError(RuntimeError):
    pass


def _json_object(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise RecommendationError("The recommendation service returned an invalid result.")
    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise RecommendationError("The recommendation service returned an invalid result.") from exc
    if not isinstance(data, dict):
        raise RecommendationError("The recommendation service returned an invalid result.")
    return data


def _clean(value: object, limit: int) -> str:
    if value is None:
        return ""
    val_str = str(value)
    return re.sub(r"\s+", " ", val_str).strip()[:limit]


def _format_match_score(value: object) -> str:
    if value is None or value == "":
        return "96% Match"
    if isinstance(value, (int, float)):
        num = float(value)
        if num <= 10:
            return f"{int(num * 10)}% Match"
        return f"{int(num)}% Match"
    s = str(value).strip()
    if s.endswith("%") or "match" in s.lower():
        return s if "match" in s.lower() else f"{s} Match"
    try:
        num = float(s)
        if num <= 10:
            return f"{int(num * 10)}% Match"
        return f"{int(num)}% Match"
    except ValueError:
        return f"{s} Match"


def _validate(data: dict) -> dict[str, Any]:
    recommendations = data.get("recommendations") or data.get("movies") or data.get("picks") or data.get("results")
    if not isinstance(recommendations, list) or len(recommendations) == 0:
        raise RecommendationError("The recommendation service returned an invalid result.")
    validated = []
    for item in recommendations[:3]:
        if not isinstance(item, dict):
            continue
        title = _clean(item.get("title") or item.get("name"), 120)
        reason = _clean(
            item.get("reason")
            or item.get("why")
            or item.get("description")
            or item.get("explanation")
            or item.get("note"),
            260,
        )
        if not title:
            continue
        raw_score = item.get("match_score") or item.get("score")
        result = {
            "title": title,
            "year": _clean(item.get("year") or item.get("release_year"), 20) or "Unknown",
            "genre": _clean(item.get("genre") or item.get("genres"), 80) or "Cinema",
            "language": _clean(item.get("language"), 80) or "English",
            "match_score": _format_match_score(raw_score),
            "reason": reason or "Acclaimed film strongly matching your cinema taste.",
        }
        validated.append(result)

    if len(validated) < 3:
        raise RecommendationError("The recommendation service returned fewer than 3 recommendations.")

    taste_summary = _clean(data.get("taste_summary") or data.get("summary") or data.get("analysis"), 320)
    return {"taste_summary": taste_summary, "recommendations": validated}


def _catalog_fallback_recommendations(preferences: dict[str, Any]) -> dict[str, Any]:
    """Catalog similarity taste matcher when external AI API is rate-limited or unavailable."""
    from services.movie_service import list_movies
    all_movies = list_movies(limit=100)
    selected_raw = preferences.get("selected_movies") or []
    selected_set = {m.lower().strip() for m in selected_raw if m}
    preferred_genre = (preferences.get("genre") or "").lower().strip()
    preferred_lang = (preferences.get("language") or "").lower().strip()

    liked_genres = set()
    liked_directors = set()
    for m in all_movies:
        if m.get("title", "").lower().strip() in selected_set:
            liked_genres.update(g.lower() for g in m.get("genres", []))
            if m.get("director"):
                liked_directors.add(m.get("director", "").lower())

    if preferred_genre and preferred_genre != "any":
        liked_genres.add(preferred_genre)

    scored = []
    for m in all_movies:
        title = m.get("title", "")
        if title.lower().strip() in selected_set:
            continue
        score = 0
        reasons = []

        m_genres = [g.lower() for g in m.get("genres", [])]
        overlap = set(m_genres).intersection(liked_genres)
        if overlap:
            score += len(overlap) * 3
            reasons.append(f"shares {' & '.join(list(overlap)[:2]).title()} themes")

        if m.get("director") and m.get("director", "").lower() in liked_directors:
            score += 4
            reasons.append(f"directed by {m.get('director')}")

        if preferred_lang and preferred_lang != "any" and preferred_lang in m.get("language", "").lower():
            score += 2

        rating = m.get("rating") or 7.0
        score += float(rating) * 0.5

        scored.append((score, m, reasons))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_picks = scored[:3] if scored else []

    recommendations = []
    for score, m, reasons in top_picks:
        pct = min(99, max(84, int(78 + score * 2.2)))
        reason_text = (
            f"Matches your taste: {', '.join(reasons)} with an acclaimed IMDb score of {m.get('rating', '8.0')}."
            if reasons
            else f"Acclaimed {', '.join(m.get('genres', ['movie'])[:2])} film that fits your selected viewing style."
        )
        recommendations.append({
            "title": m.get("title", "Movie"),
            "year": m.get("year", "Unknown"),
            "genre": ", ".join(m.get("genres", ["Drama"])[:2]),
            "language": m.get("language", "English"),
            "match_score": f"{pct}% Match",
            "reason": reason_text,
        })

    if selected_raw:
        summary_text = (
            f"Based on your appreciation of {', '.join(selected_raw[:3])}, you love immersive stories "
            f"with sharp emotional stakes, compelling character journeys, and acclaimed cinematic direction."
        )
    else:
        summary_text = "Based on your preferences, these top-rated cinema masterworks deliver outstanding storytelling and memorable depth."

    return {"taste_summary": summary_text, "recommendations": recommendations}


def get_recommendations(preferences: dict[str, Any]) -> dict[str, Any]:
    if not Config.OPENROUTER_API_KEY or not Config.OPENROUTER_MODEL:
        return _catalog_fallback_recommendations(preferences)

    selected_movies = preferences.get("selected_movies") or []
    if selected_movies:
        movie_context = f"The user specifically LOVES and has selected these movies: {', '.join(selected_movies)}."
    else:
        movie_context = "The user has not selected specific past movies, but has the following preferences."

    prompt = f"""You are an elite cinema taste-matcher and movie recommendation assistant.

{movie_context}

User preferences:
- Mood: {preferences.get('mood', 'Any')}
- Preferred genre: {preferences.get('genre', 'Any')}
- Preferred language: {preferences.get('language', 'Any')}
- Custom details: {preferences.get('request', 'None')}

Task:
1. Briefly analyze why the user loves these movies (themes, tone, pacing, emotions) in 1 sentence for 'taste_summary'.
2. Recommend exactly three real movies that match their taste.
3. For each movie, explain how it connects to the movies they like.

Return ONLY valid JSON in this exact structure:
{{
  "taste_summary": "1 sentence analyzing what makes them love movies.",
  "recommendations": [
    {{
      "title": "Movie title",
      "year": "Release year",
      "genre": "Main genres",
      "language": "Main language",
      "match_score": "98% Match",
      "reason": "Specific reason connecting this movie to what they like (under 30 words)."
    }}
  ]
}}

Rules: exactly 3 recommendations; real movies only; each reason under 30 words; no markdown outside JSON."""

    try:
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=Config.OPENROUTER_API_KEY)
        response = client.chat.completions.create(
            model=Config.OPENROUTER_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=900,
            response_format={"type": "json_object"},
            extra_headers={"HTTP-Referer": Config.APP_URL, "X-Title": Config.APP_NAME},
            timeout=Config.AI_TIMEOUT_SECONDS,
        )
        content = response.choices[0].message.content or ""
        return _validate(_json_object(content))
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print(f"[recommendation_service] OpenRouter notice: {exc}. Content was: {repr(content if 'content' in locals() else None)}. Using smart catalog matching.", flush=True)
        return _catalog_fallback_recommendations(preferences)
