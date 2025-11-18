import os, requests, sqlite3
import logging
from dotenv import load_dotenv
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

DB = os.getenv("DATABASE_URL", "sqlite:///./db.sqlite").replace("sqlite:///./","./")

from auth_helpers import refresh_access_token
from token_manager import load_token
from db_utils import create_tables
from spotify_ops import get_artist_genres

def get_recently_played(access_token, limit=50):
    """Fetch recently played tracks from Spotify (single page)"""
    try:
        if not access_token:
            raise ValueError("access_token is required")
        if limit < 1 or limit > 50:
            raise ValueError("limit must be between 1 and 50")
        
        headers = {"Authorization": f"Bearer {access_token}"}
        url = f"https://api.spotify.com/v1/me/player/recently-played?limit={limit}"
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        logger.info(f"Retrieved {len(r.json().get('items', []))} recently played tracks")
        return r.json()
    except requests.exceptions.Timeout:
        logger.error("Timeout fetching recently played tracks")
        raise
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error fetching recently played: {e.response.status_code}")
        raise
    except Exception as e:
        logger.error(f"Error fetching recently played tracks: {e}")
        raise

def get_all_recently_played(access_token, limit=None):
    """Fetch recently played tracks from Spotify.
    
    IMPORTANT: Spotify's /me/player/recently-played endpoint has a documented
    limitation - it only returns the 50 most recent plays. There is no way to
    paginate further back using pagination, before/after cursors, or date ranges.
    
    This is a Spotify API design limitation, not a bug in this code.
    
    Args:
        access_token: Spotify API access token
        limit: Maximum number of tracks to fetch (capped at 50 by Spotify)
    """
    try:
        if not access_token:
            raise ValueError("access_token is required")
        
        # Note: Spotify API caps recently-played at 50 items max
        if limit is None:
            limit = 50
        limit = min(limit, 50)  # Enforce Spotify's hard limit
        
        headers = {"Authorization": f"Bearer {access_token}"}
        
        logger.info(f"Fetching recently played tracks (limit: {limit})...")
        logger.warning("⚠️  NOTE: Spotify API limits recently-played to 50 items max. Cannot fetch more than this.")
        
        try:
            url = f"https://api.spotify.com/v1/me/player/recently-played?limit={limit}"
            r = requests.get(url, headers=headers, timeout=10)
            r.raise_for_status()
            data = r.json()
            items = data.get("items", [])
            
            logger.info(f"Retrieved {len(items)} tracks")
            
            if len(items) < limit:
                logger.warning(f"Expected {limit} items but got {len(items)}")
                
            return {"items": items, "total": len(items)}
            
        except requests.exceptions.Timeout:
            logger.error("Timeout fetching recently played tracks")
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error fetching recently played: {e.response.status_code}")
            raise
        
    except Exception as e:
        logger.error(f"Error fetching recently played tracks: {e}")
        raise

def get_last_download_time():
    """Get the timestamp of the last successful download"""
    try:
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute("SELECT last_downloaded_at FROM download_history ORDER BY download_completed_at DESC LIMIT 1")
        result = cur.fetchone()
        conn.close()
        if result and result[0]:
            return result[0]
        return None
    except Exception as e:
        logger.warning(f"Could not retrieve last download time: {e}")
        return None

def save_download_history(timestamp, count):
    """Save download history for incremental updates"""
    try:
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO download_history (last_downloaded_at, songs_downloaded) VALUES (?, ?)",
            (timestamp, count)
        )
        conn.commit()
        conn.close()
        logger.info(f"Saved download history: {count} songs, last downloaded at {timestamp}")
    except Exception as e:
        logger.error(f"Error saving download history: {e}")

def get_audio_features(access_token, ids):
    """Fetch audio features for multiple tracks"""
    try:
        if not access_token:
            raise ValueError("access_token is required")
        if not ids or not isinstance(ids, list):
            raise ValueError("ids must be a non-empty list")
        if len(ids) > 100:
            raise ValueError("Can only request features for max 100 tracks at a time")
        
        headers = {"Authorization": f"Bearer {access_token}"}
        url = "https://api.spotify.com/v1/audio-features"
        params = {"ids": ",".join(ids)}
        r = requests.get(url, headers=headers, params=params, timeout=10)
        r.raise_for_status()
        logger.info(f"Retrieved audio features for {len(ids)} tracks")
        return r.json()
    except requests.exceptions.Timeout:
        logger.error("Timeout fetching audio features")
        raise
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error fetching audio features: {e.response.status_code}")
        raise
    except Exception as e:
        logger.error(f"Error fetching audio features: {e}")
        raise

def deduplicate_consecutive_plays(items):
    """Remove consecutive duplicate plays of the same song (pauses/replays).
    
    If the same track_id appears multiple times in a row within a short timeframe (5 minutes),
    keep only the first occurrence and use the latest timestamp as the actual play time.
    This treats pause/resume as a single play session.
    
    Args:
        items: List of play items from Spotify API
        
    Returns:
        Deduplicated list of items
    """
    if not items:
        return items
    
    deduplicated = []
    i = 0
    
    while i < len(items):
        current_item = items[i]
        current_track_id = current_item["track"]["id"]
        current_played_at = current_item["played_at"]
        
        # Check if next items are the same track
        j = i + 1
        last_played_at = current_played_at
        
        while j < len(items):
            next_item = items[j]
            next_track_id = next_item["track"]["id"]
            next_played_at = next_item["played_at"]
            
            # Check if same track and within 5 minutes
            from datetime import datetime as dt, timedelta
            current_time = dt.fromisoformat(current_played_at.replace('Z', '+00:00'))
            next_time = dt.fromisoformat(next_played_at.replace('Z', '+00:00'))
            time_diff = (current_time - next_time).total_seconds()
            
            if next_track_id == current_track_id and abs(time_diff) < 300:  # 5 minutes
                logger.info(f"Found duplicate play: {current_track_id} at {current_played_at} and {next_played_at}")
                last_played_at = next_played_at  # Update to the latest occurrence
                j += 1
            else:
                break
        
        # Use the earliest played_at timestamp (first play) for skip detection accuracy
        deduplicated.append(current_item)
        i = j if j > i + 1 else i + 1
    
    if len(deduplicated) < len(items):
        logger.info(f"Deduplicated {len(items) - len(deduplicated)} consecutive duplicate plays")
    
    return deduplicated

def main(fetch_all=True, initial_download=False, limit=None):
    """Main ingestion process
    
    Args:
        fetch_all (bool): If True, fetch all available tracks using pagination.
                         If False, fetch only the last 50 tracks.
        initial_download (bool): If True, fetch up to 300 songs for initial setup.
                                If False, fetch only new songs since last download.
        limit (int): Maximum number of tracks to fetch (used for initial download).
    """
    try:
        logger.info(f"Starting music ingestion... (initial_download={initial_download}, limit={limit})")
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"Script directory: {os.path.dirname(os.path.abspath(__file__))}")
        
        # Try multiple times to load token (with debugging)
        token_info = load_token()
        logger.info(f"Token loading result: {token_info is not None}")
        
        if not token_info:
            logger.error("load_token() returned None or empty dict - checking file system directly")
            # Direct check
            import sys
            for path_item in [
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "tokens.json"),
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "tokens.json"),
                "tokens.json"
            ]:
                logger.info(f"Checking: {path_item} -> exists={os.path.exists(path_item)}")
            raise ValueError("No valid token found in tokens.json. Please authenticate first via the dashboard.")
        
        if "refresh_token" not in token_info:
            logger.error(f"Token loaded but refresh_token missing. Keys available: {list(token_info.keys())}")
            raise ValueError("No valid token found in tokens.json. Please authenticate first via the dashboard.")
        
        refresh_token = token_info["refresh_token"]
        logger.info("Loaded refresh token from tokens.json")
        
        # Get access token
        tokens = refresh_access_token(refresh_token)
        access_token = tokens["access_token"]
        logger.info("Access token obtained successfully")
        
        # Setup database
        create_tables()  # Create all tables including plays
        
        # Determine what to fetch
        if initial_download:
            logger.info(f"Initial download: Fetching Spotify recently played tracks...")
            data = get_all_recently_played(access_token, limit=50)
        else:
            # Incremental download: fetch from last download time
            last_download = get_last_download_time()
            if last_download:
                logger.info(f"Incremental download: Fetching new songs since {last_download}...")
                data = get_all_recently_played(access_token, limit=50)
            else:
                logger.info("No previous download found. Fetching recently played tracks...")
                data = get_all_recently_played(access_token, limit=50)
        
        # Deduplicate consecutive plays (pause/resume handling)
        items = data.get("items", [])
        deduplicated_items = deduplicate_consecutive_plays(items)
        data["items"] = deduplicated_items
        
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        track_ids = []
        track_artist_map = {}
        new_plays_count = 0
        
        # Insert tracks and plays
        for item in data.get("items", []):
            try:
                t = item["track"]
                tid = t["id"]
                played_at = item["played_at"]  # This is ISO format datetime from Spotify
                artists = ", ".join([a["name"] for a in t["artists"]])
                
                # Determine primary artist id (first listed artist)
                primary_artist_id = None
                if t.get("artists") and isinstance(t["artists"], list) and len(t["artists"]) > 0:
                    primary_artist_id = t["artists"][0].get("id")

                # Fetch artist genres (may be empty)
                genre_str = None
                try:
                    if primary_artist_id:
                        genres = get_artist_genres(access_token, primary_artist_id)
                        # Pick the top genre if available, otherwise None
                        genre_str = genres[0] if genres else None
                except Exception:
                    genre_str = None

                # Insert track using correct column names (include genre)
                cur.execute(
                    "INSERT OR IGNORE INTO tracks(track_id, track_name, artist, duration_ms, popularity, genre) VALUES (?,?,?,?,?,?)",
                    (tid, t["name"], artists, t.get("duration_ms", 0), t.get("popularity", 0), genre_str)
                )
                
                # Check if this play record already exists (for incremental updates)
                cur.execute("SELECT COUNT(*) FROM plays WHERE track_id = ? AND played_at = ?", (tid, played_at))
                exists = cur.fetchone()[0] > 0
                
                if not exists:
                    # Insert play record with full datetime (played_at from Spotify is ISO format)
                    cur.execute(
                        "INSERT INTO plays(track_id, played_at, context) VALUES (?,?,?)",
                        (tid, played_at, str(item.get("context")))
                    )
                    new_plays_count += 1
                
                if tid not in track_ids:
                    track_ids.append(tid)
                    # remember primary artist id for potential backfill/update
                    track_artist_map[tid] = primary_artist_id
            except KeyError as e:
                logger.warning(f"Skipping malformed track item: missing {e}")
                continue
        
        conn.commit()
        # Backfill/update genre for tracks that may not have been stored (or were ignored previously)
        try:
            for tid in track_ids:
                # only update if genre is missing or empty
                cur.execute("SELECT genre FROM tracks WHERE track_id = ?", (tid,))
                row = cur.fetchone()
                current_genre = row[0] if row else None
                if not current_genre:
                    primary_artist_id = track_artist_map.get(tid)
                    if primary_artist_id:
                        genres = get_artist_genres(access_token, primary_artist_id)
                        genre_str = genres[0] if genres else None
                        if genre_str:
                            cur.execute("UPDATE tracks SET genre = ? WHERE track_id = ?", (genre_str, tid))
            conn.commit()
        except Exception as e:
            logger.warning(f"Failed to backfill genres: {e}")
        logger.info(f"Inserted {new_plays_count} new plays, {len(track_ids)} unique tracks into database")
        
        # Fetch and store audio features in batches
        logger.info("Fetching audio features...")
        for i in range(0, len(track_ids), 100):
            batch = track_ids[i:i+100]
            try:
                features = get_audio_features(access_token, batch)
                for f in features.get("audio_features", []):
                    if not f:
                        continue
                    # Update track with audio features
                    cur.execute(
                        "UPDATE tracks SET energy=?, danceability=?, valence=?, tempo=? WHERE track_id=?",
                        (
                            f.get("energy"), 
                            f.get("danceability"),
                            f.get("valence"),
                            f.get("tempo"),
                            f["id"]
                        )
                    )
                    logger.debug(f"Updated audio features for track {f['id']}")
            except Exception as e:
                logger.error(f"Error fetching features for batch {i//100 + 1}: {e}")
                continue
        
        conn.commit()
        conn.close()
        
        # Save download history
        if new_plays_count > 0:
            latest_play = max([item["played_at"] for item in data.get("items", [])], default=None)
            if latest_play:
                save_download_history(latest_play, new_plays_count)
        
        logger.info("Music ingestion completed successfully")
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise
    except Exception as e:
        logger.error(f"Fatal error during ingestion: {e}")
        raise

if __name__ == "__main__":
    main()
