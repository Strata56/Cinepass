from __future__ import annotations

import json
import re

from config import Config


class SummaryError(RuntimeError):
    pass


def _clean(value: object, limit: int) -> str:
    return re.sub(r"\s+", " ", value if isinstance(value, str) else "").strip()[:limit]


def _parse_result(raw: str, fallback_title: str) -> dict[str, str]:
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", (raw or "").strip(), flags=re.IGNORECASE)
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        raise SummaryError("The movie summary could not be generated.")
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError as exc:
        raise SummaryError("The movie summary could not be generated.") from exc
    result = {
        "title": _clean(data.get("title"), 150) or fallback_title,
        "summary": _clean(data.get("summary"), 1300),
        "genre": _clean(data.get("genre"), 160),
        "mood": _clean(data.get("mood"), 160),
        "suitable_for": _clean(data.get("suitable_for"), 220),
    }
    if not all(result.values()):
        raise SummaryError("The movie summary could not be generated.")
    return result


def _prompt(movie: dict) -> str:
    genres = ", ".join(movie.get("genres") or ["Not available"])
    description = _clean(movie.get("description"), 3000)
    return f"""Generate a short spoiler-free movie summary using only the supplied movie information.

Movie title: {movie.get('title', 'Not available')}
Genre: {genres}
Description: {description}

Return only valid JSON in this exact format:
{{"title":"Movie title","summary":"An 80 to 120 word spoiler-free summary","genre":"Main genre","mood":"Overall movie mood","suitable_for":"Suitable audience"}}

Rules: do not reveal the ending or major twists; do not invent characters, events, actors, or facts; use simple language; do not use markdown or text outside JSON."""


def _with_gemini(prompt: str) -> str:
    if not Config.GEMINI_API_KEY or not Config.GEMINI_MODEL:
        raise SummaryError("AI summaries are unavailable. Configure the selected summary provider.")
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=Config.GEMINI_API_KEY)
        response = client.models.generate_content(
            model=Config.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.3),
        )
        return response.text or ""
    except SummaryError:
        raise
    except Exception as exc:
        raise SummaryError("The movie summary could not be generated.") from exc


def _with_openai(prompt: str) -> str:
    if not Config.OPENAI_API_KEY or not Config.OPENAI_MODEL:
        raise SummaryError("AI summaries are unavailable. Configure the selected summary provider.")
    try:
        from openai import AuthenticationError, OpenAI, RateLimitError

        client = OpenAI(api_key=Config.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=Config.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            max_completion_tokens=800,
            timeout=Config.AI_TIMEOUT_SECONDS,
        )
        return response.choices[0].message.content or ""
    except RateLimitError as exc:
        raise SummaryError("OpenAI summary quota is unavailable. Add API billing or choose another summary provider.") from exc
    except AuthenticationError as exc:
        raise SummaryError("The configured OpenAI API key could not be authenticated.") from exc
    except SummaryError:
        raise
    except Exception as exc:
        raise SummaryError("The movie summary could not be generated.") from exc


def _with_openrouter(prompt: str) -> str:
    if not Config.OPENROUTER_API_KEY or not Config.SUMMARY_OPENROUTER_MODEL:
        raise SummaryError("AI summaries are unavailable. Configure the OpenRouter API key and model.")
    try:
        from openai import OpenAI

        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=Config.OPENROUTER_API_KEY)
        response = client.chat.completions.create(
            model=Config.SUMMARY_OPENROUTER_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "movie_summary",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "summary": {"type": "string"},
                            "genre": {"type": "string"},
                            "mood": {"type": "string"},
                            "suitable_for": {"type": "string"},
                        },
                        "required": ["title", "summary", "genre", "mood", "suitable_for"],
                        "additionalProperties": False,
                    },
                },
            },
            max_tokens=800,
            temperature=0.3,
            timeout=Config.AI_TIMEOUT_SECONDS,
            extra_headers={"HTTP-Referer": Config.APP_URL, "X-Title": Config.APP_NAME},
        )
        return response.choices[0].message.content or ""
    except SummaryError:
        raise
    except Exception as exc:
        raise SummaryError("The movie summary could not be generated through OpenRouter.") from exc


def generate_summary(movie: dict) -> tuple[dict[str, str], str]:
    prompt = _prompt(movie)
    provider = Config.SUMMARY_PROVIDER
    if provider == "gemini":
        raw = _with_gemini(prompt)
    elif provider == "openai":
        raw = _with_openai(prompt)
    else:
        raw = _with_openrouter(prompt)
        try:
            return _parse_result(raw, movie.get("title", "Movie")), provider
        except SummaryError:
            # Some OpenRouter providers occasionally violate structured output;
            # retry once with the same schema before returning a friendly error.
            raw = _with_openrouter(prompt)
    return _parse_result(raw, movie.get("title", "Movie")), provider
