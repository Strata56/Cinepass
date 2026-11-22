from __future__ import annotations

import time
import sys
from pathlib import Path
from datetime import datetime, timezone

_backend_path = str(Path(__file__).resolve().parent)
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

from config import Config
from database import get_movies_collection, initialize_database
from services.movie_scraper import ScraperError, fetch_movie_poster
from utils.validators import normalize_movie_title


def now():
    return datetime.now(timezone.utc)


MOVIES = [
    ("Interstellar", "2014", ["Science Fiction", "Drama"], "English", "169 minutes", "Christopher Nolan", ["Matthew McConaughey", "Anne Hathaway", "Jessica Chastain"], "A group of explorers travels through space in search of a future home for humanity.", 8.7),
    ("The Dark Knight", "2008", ["Action", "Crime", "Drama"], "English", "152 minutes", "Christopher Nolan", ["Christian Bale", "Heath Ledger", "Aaron Eckhart"], "Batman faces a criminal mastermind who challenges Gotham City and its protector.", 9.0),
    ("Avengers: Endgame", "2019", ["Action", "Science Fiction"], "English", "181 minutes", "Anthony and Joe Russo", ["Robert Downey Jr.", "Chris Evans", "Mark Ruffalo"], "The Avengers reunite for a high-stakes mission after a devastating loss.", 8.4),
    ("3 Idiots", "2009", ["Comedy", "Drama"], "Hindi", "170 minutes", "Rajkumar Hirani", ["Aamir Khan", "R. Madhavan", "Sharman Joshi"], "Three engineering students form a close friendship while questioning the pressure-filled education system.", 8.4),
    ("Dangal", "2016", ["Biography", "Drama", "Sport"], "Hindi", "161 minutes", "Nitesh Tiwari", ["Aamir Khan", "Fatima Sana Shaikh", "Sanya Malhotra"], "A former wrestler trains his daughters to pursue excellence in competitive wrestling.", 8.3),
    ("Zindagi Na Milegi Dobara", "2011", ["Comedy", "Drama", "Road"], "Hindi", "155 minutes", "Zoya Akhtar", ["Hrithik Roshan", "Farhan Akhtar", "Abhay Deol"], "Three friends take a life-changing road trip through Spain before a wedding.", 8.2),
    ("Hera Pheri", "2000", ["Comedy", "Crime"], "Hindi", "156 minutes", "Priyadarshan", ["Akshay Kumar", "Suniel Shetty", "Paresh Rawal"], "Three cash-strapped men become entangled in a chaotic kidnapping scheme.", 8.2),
    ("Taare Zameen Par", "2007", ["Drama", "Family"], "Hindi", "165 minutes", "Aamir Khan", ["Darsheel Safary", "Aamir Khan", "Tisca Chopra"], "A struggling child finds encouragement and understanding through a compassionate teacher.", 8.3),
    ("Jab We Met", "2007", ["Romance", "Comedy", "Drama"], "Hindi", "138 minutes", "Imtiaz Ali", ["Shahid Kapoor", "Kareena Kapoor"], "A quiet businessman and an outspoken young woman meet during an unexpected train journey.", 7.9),
    ("Chhichhore", "2019", ["Comedy", "Drama"], "Hindi", "143 minutes", "Nitesh Tiwari", ["Sushant Singh Rajput", "Shraddha Kapoor", "Varun Sharma"], "A group of former college friends reconnect to offer perspective during a difficult family moment.", 8.3),
    ("Coco", "2017", ["Animation", "Family", "Fantasy"], "English", "105 minutes", "Lee Unkrich", ["Anthony Gonzalez", "Gael Garcia Bernal", "Benjamin Bratt"], "A music-loving boy embarks on an extraordinary journey that connects him with his family history.", 8.4),
    ("The Martian", "2015", ["Science Fiction", "Adventure"], "English", "141 minutes", "Ridley Scott", ["Matt Damon", "Jessica Chastain", "Jeff Daniels"], "An astronaut uses ingenuity and perseverance after being stranded far from home.", 8.0),
    ("Piku", "2015", ["Comedy", "Drama"], "Hindi", "123 minutes", "Shoojit Sircar", ["Deepika Padukone", "Amitabh Bachchan", "Irrfan Khan"], "A strong-willed architect takes an eventful road trip with her eccentric father and their patient driver.", 7.6),
    ("Queen", "2013", ["Comedy", "Drama"], "Hindi", "146 minutes", "Vikas Bahl", ["Kangana Ranaut", "Rajkummar Rao", "Lisa Haydon"], "A young woman travels alone after her wedding plans change and discovers a new sense of independence.", 8.1),
    ("Andhadhun", "2018", ["Crime", "Comedy", "Thriller"], "Hindi", "139 minutes", "Sriram Raghavan", ["Ayushmann Khurrana", "Tabu", "Radhika Apte"], "A pianist becomes caught in a dangerous chain of events after witnessing something unexpected.", 8.2),
    ("Drishyam", "2015", ["Crime", "Drama", "Thriller"], "Hindi", "163 minutes", "Nishikant Kamat", ["Ajay Devgn", "Tabu", "Shriya Saran"], "A devoted father relies on careful planning when his family becomes involved in a police investigation.", 8.2),
    ("Lagaan", "2001", ["Drama", "Sport"], "Hindi", "224 minutes", "Ashutosh Gowariker", ["Aamir Khan", "Gracy Singh", "Rachel Shelley"], "Villagers under colonial rule accept a difficult cricket challenge that could free them from a heavy tax.", 8.1),
    ("Swades", "2004", ["Drama"], "Hindi", "189 minutes", "Ashutosh Gowariker", ["Shah Rukh Khan", "Gayatri Joshi", "Kishori Ballal"], "An engineer living abroad returns to India and reconnects with a village and its community.", 8.2),
    ("Barfi!", "2012", ["Comedy", "Drama", "Romance"], "Hindi", "151 minutes", "Anurag Basu", ["Ranbir Kapoor", "Priyanka Chopra", "Ileana D'Cruz"], "A warm-hearted young man forms meaningful relationships while navigating life through humor and resilience.", 8.1),
    ("Kahaani", "2012", ["Mystery", "Thriller"], "Hindi", "122 minutes", "Sujoy Ghosh", ["Vidya Balan", "Parambrata Chatterjee", "Nawazuddin Siddiqui"], "A pregnant woman searches through Kolkata for her missing husband with the help of a police officer.", 8.1),
    ("The Shawshank Redemption", "1994", ["Drama"], "English", "142 minutes", "Frank Darabont", ["Tim Robbins", "Morgan Freeman", "Bob Gunton"], "A banker serving a prison sentence builds an enduring friendship and quietly holds on to hope.", 9.3),
    ("Inception", "2010", ["Action", "Science Fiction", "Thriller"], "English", "148 minutes", "Christopher Nolan", ["Leonardo DiCaprio", "Joseph Gordon-Levitt", "Elliot Page"], "A skilled specialist enters layered dreams to carry out a complicated and deeply personal assignment.", 8.8),
    ("The Matrix", "1999", ["Action", "Science Fiction"], "English", "136 minutes", "Lana and Lilly Wachowski", ["Keanu Reeves", "Laurence Fishburne", "Carrie-Anne Moss"], "A computer programmer begins questioning reality after meeting a group of mysterious rebels.", 8.7),
    ("Parasite", "2019", ["Drama", "Thriller"], "Korean", "132 minutes", "Bong Joon Ho", ["Song Kang-ho", "Lee Sun-kyun", "Cho Yeo-jeong"], "A struggling family gradually becomes involved with a wealthy household through an unusual opportunity.", 8.5),
    ("Spirited Away", "2001", ["Animation", "Adventure", "Fantasy"], "Japanese", "125 minutes", "Hayao Miyazaki", ["Rumi Hiiragi", "Miyu Irino", "Mari Natsuki"], "A young girl enters a mysterious spirit world and must find courage to help her family return home.", 8.6),
    ("The Grand Budapest Hotel", "2014", ["Comedy", "Drama"], "English", "99 minutes", "Wes Anderson", ["Ralph Fiennes", "Tony Revolori", "Saoirse Ronan"], "A dedicated hotel concierge and his young lobby boy become involved in a lively mystery.", 8.1),
    ("Knives Out", "2019", ["Mystery", "Comedy", "Crime"], "English", "130 minutes", "Rian Johnson", ["Daniel Craig", "Chris Evans", "Ana de Armas"], "A detective investigates a famous writer's unusual death within a complicated family gathering.", 7.9),
    ("Everything Everywhere All at Once", "2022", ["Action", "Comedy", "Science Fiction"], "English", "139 minutes", "Daniel Kwan and Daniel Scheinert", ["Michelle Yeoh", "Ke Huy Quan", "Stephanie Hsu"], "A laundromat owner is drawn into a sprawling adventure that challenges her relationships and sense of possibility.", 7.8),
]


def make_movie(values):
    title, year, genres, language, duration, director, cast, description, rating, *optional = values
    poster_url = optional[0] if optional else ""
    source_url = optional[1] if len(optional) > 1 else ""
    timestamp = now()
    return {
        "title": title, "normalized_title": normalize_movie_title(title), "year": year, "genres": genres,
        "language": language, "duration": duration, "director": director, "cast": cast,
        "description": description, "poster_url": poster_url, "rating": rating, "source_url": source_url,
        "data_source": "seed", "ai_summary": None, "summary_genre": None, "summary_mood": None,
        "summary_suitable_for": None, "summary_provider": None, "created_at": timestamp, "updated_at": timestamp,
    }


if __name__ == "__main__":
    Config.validate()
    class AppConfig(dict):
        def __getitem__(self, key):
            return getattr(Config, key)
    class App:
        config = AppConfig()
    if not initialize_database(App()):
        print("The movie database is currently unavailable.")
        raise SystemExit(1)
    collection = get_movies_collection()
    if "--fallback-only" in sys.argv:
        result = collection.update_many(
            {"$or": [{"poster_url": ""}, {"poster_url": None}, {"poster_url": {"$exists": False}}]},
            {"$set": {"poster_url": "/static/images/movie-placeholder.svg"}},
        )
        print(f"Added local poster fallbacks to {result.modified_count} movies.")
        raise SystemExit(0)
    posters_added = 0
    for index, values in enumerate(MOVIES, start=1):
        movie = make_movie(values)
        existing = collection.find_one({"normalized_title": movie["normalized_title"]}, {"poster_url": 1, "source_url": 1})
        poster_url = movie.get("poster_url") or (existing or {}).get("poster_url", "")
        source_url = movie.get("source_url") or (existing or {}).get("source_url", "")
        if not poster_url:
            for attempt in range(2):
                try:
                    poster_url, source_url = fetch_movie_poster(movie["title"], timeout=12)
                    if poster_url:
                        posters_added += 1
                        break
                except ScraperError:
                    poster_url = ""
                time.sleep(2 + attempt * 2)
            time.sleep(1.5)
        movie["poster_url"] = poster_url
        movie["source_url"] = source_url
        created_at = movie.pop("created_at")
        summary_defaults = {
            "ai_summary": movie.pop("ai_summary"),
            "summary_genre": movie.pop("summary_genre"),
            "summary_mood": movie.pop("summary_mood"),
            "summary_suitable_for": movie.pop("summary_suitable_for"),
            "summary_provider": movie.pop("summary_provider"),
            "created_at": created_at,
        }
        collection.update_one(
            {"normalized_title": movie["normalized_title"]},
            {"$set": movie, "$setOnInsert": summary_defaults},
            upsert=True,
        )
        print(f"[{index:02}/{len(MOVIES)}] {movie['title']}")
    print(f"Seeded {len(MOVIES)} curated movies; added {posters_added} poster images.")
