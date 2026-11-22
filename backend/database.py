from __future__ import annotations

from typing import Optional

from flask import current_app
from pymongo import ASCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import PyMongoError


_client: Optional[MongoClient] = None
_database: Optional[Database] = None
_connection_error: Optional[str] = None


class DatabaseUnavailable(RuntimeError):
    pass


def initialize_database(app) -> bool:
    """Connect to MongoDB with error logging and friendly fallback."""
    global _client, _database, _connection_error
    try:
        uri = app.config.get("MONGODB_URI", "mongodb://localhost:27017/")
        db_name = app.config.get("MONGODB_DATABASE", "cinesuggest_ai")
        timeout = app.config.get("MONGODB_TIMEOUT_MS", 15000)

        _client = MongoClient(
            uri,
            serverSelectionTimeoutMS=timeout,
            connectTimeoutMS=timeout,
        )
        _client.admin.command("ping")
        _database = _client[db_name]
        try:
            _database.movies.create_index([("normalized_title", ASCENDING)], unique=True)
        except Exception:
            pass
        _connection_error = None
        print(f"[MongoDB] Connected to '{db_name}' successfully.", flush=True)
        return True
    except Exception as exc:
        _client = None
        _database = None
        _connection_error = "The movie database is currently unavailable."
        print(f"[MongoDB] Connection failed: {exc}", flush=True)
        return False


def get_database() -> Database:
    global _database
    if _database is None:
        try:
            from flask import current_app
            if current_app:
                initialize_database(current_app)
        except Exception as exc:
            print(f"[MongoDB] Auto-reconnect failed: {exc}", flush=True)

    if _database is None:
        raise DatabaseUnavailable(_connection_error or "The movie database is currently unavailable.")
    return _database


def get_movies_collection() -> Collection:
    return get_database().movies


def is_database_available() -> bool:
    return _database is not None


def database_error_message() -> str:
    return _connection_error or "The movie database is currently unavailable."


def close_database(_: object = None) -> None:
    global _client, _database
    if _client is not None:
        _client.close()
    _client = None
    _database = None
