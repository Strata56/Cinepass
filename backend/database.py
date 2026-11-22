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
    """Connect once on startup; never prevent Flask from starting."""
    global _client, _database, _connection_error
    try:
        _client = MongoClient(
            app.config["MONGODB_URI"],
            serverSelectionTimeoutMS=app.config["MONGODB_TIMEOUT_MS"],
            connectTimeoutMS=app.config["MONGODB_TIMEOUT_MS"],
        )
        _client.admin.command("ping")
        _database = _client[app.config["MONGODB_DATABASE"]]
        _database.movies.create_index([( "normalized_title", ASCENDING)], unique=True)
        _connection_error = None
        return True
    except PyMongoError:
        _client = None
        _database = None
        _connection_error = "The movie database is currently unavailable."
        return False


def get_database() -> Database:
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
