import sqlite3
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = "db.sqlite"

def create_tables():
    """Create necessary database tables"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Tabla de usuarios
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            display_name TEXT,
            email TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Tabla de tracks
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tracks (
            track_id TEXT PRIMARY KEY,
            track_name TEXT NOT NULL,
            artist TEXT,
            duration_ms INTEGER,
            popularity INTEGER,
            genre TEXT,
            energy REAL,
            danceability REAL,
            valence REAL,
            tempo REAL,
            mood TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            user_id TEXT,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
        """)
        
        # Tabla de plays (when songs were played)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS plays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id TEXT NOT NULL,
            played_at DATETIME,
            context TEXT,
            mood_tag INTEGER,
            mood_when_listening INTEGER,
            theme_tag TEXT,
            tagged_at DATETIME,
            FOREIGN KEY(track_id) REFERENCES tracks(track_id)
        )
        """)
        
        # Tabla para rastrear último descarga (para descargas incrementales)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS download_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            last_downloaded_at DATETIME,
            songs_downloaded INTEGER,
            download_completed_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        conn.commit()
        conn.close()
        logger.info("Database tables created/verified successfully")
    except sqlite3.Error as e:
        logger.error(f"Database error creating tables: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating tables: {e}")
        raise

def insert_user(user_id, display_name, email):
    """Insert or update user information"""
    try:
        if not user_id:
            raise ValueError("user_id cannot be empty")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO users (user_id, display_name, email)
        VALUES (?, ?, ?)
        """, (user_id, display_name, email))
        conn.commit()
        conn.close()
        logger.info(f"User {user_id} inserted/updated successfully")
    except sqlite3.Error as e:
        logger.error(f"Database error inserting user: {e}")
        raise
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error inserting user: {e}")
        raise

def insert_track(track):
    """Insert a track into the database"""
    try:
        if not track or "id" not in track or "name" not in track or "user_id" not in track:
            raise ValueError("Track must have 'id', 'name', and 'user_id' fields")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR IGNORE INTO tracks 
        (track_id, track_name, artist, genre, energy, danceability, valence, tempo, mood, timestamp, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            track["id"], track["name"], track.get("artist", ""),
            track.get("genre", ""), track.get("energy"), 
            track.get("danceability"), track.get("valence"),
            track.get("tempo"), track.get("mood", ""), 
            datetime.now(), track["user_id"]
        ))
        conn.commit()
        conn.close()
        logger.info(f"Track {track['id']} inserted successfully")
    except sqlite3.Error as e:
        logger.error(f"Database error inserting track: {e}")
        raise
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error inserting track: {e}")
        raise

def get_top_tracks(user_id, limit=10):
    """Retrieve top tracks for a user"""
    try:
        if not user_id:
            raise ValueError("user_id cannot be empty")
        
        if limit < 1:
            raise ValueError("limit must be greater than 0")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
        SELECT track_name, artist FROM tracks
        WHERE user_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """, (user_id, limit))
        rows = cursor.fetchall()
        conn.close()
        logger.info(f"Retrieved {len(rows)} top tracks for user {user_id}")
        return [{"track_name": r[0], "artist": r[1]} for r in rows]
    except sqlite3.Error as e:
        logger.error(f"Database error retrieving top tracks: {e}")
        raise
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving top tracks: {e}")
        raise

def get_recent_tracks(user_id, limit=10):
    """Retrieve recent tracks for a user (alias for get_top_tracks)"""
    return get_top_tracks(user_id, limit)

def get_all_tracks(user_id):
    """Retrieve all tracks for a user"""
    try:
        if not user_id:
            raise ValueError("user_id cannot be empty")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
        SELECT track_id, track_name, artist, genre FROM tracks
        WHERE user_id = ?
        ORDER BY timestamp DESC
        """, (user_id,))
        rows = cursor.fetchall()
        conn.close()
        logger.info(f"Retrieved {len(rows)} total tracks for user {user_id}")
        return [{"track_id": r[0], "track_name": r[1], "artist": r[2], "genre": r[3]} for r in rows]
    except sqlite3.Error as e:
        logger.error(f"Database error retrieving all tracks: {e}")
        raise
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving all tracks: {e}")
        raise
