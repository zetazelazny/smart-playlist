import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_playlist(access_token, user_id, name, description="", public=False):
    """Create a playlist for the specified user"""
    try:
        if not access_token or not user_id or not name:
            raise ValueError("access_token, user_id, and name are required")
        
        url = f"https://api.spotify.com/v1/users/{user_id}/playlists"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "name": name,
            "description": description,
            "public": public
        }
        r = requests.post(url, headers=headers, json=payload, timeout=10)
        r.raise_for_status()
        logger.info(f"Playlist created: {name}")
        return r.json()
    except requests.exceptions.Timeout:
        logger.error("Timeout while creating playlist")
        raise
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error creating playlist: {e.response.status_code} - {e.response.text}")
        raise
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating playlist: {e}")
        raise

def add_tracks_to_playlist(access_token, playlist_id, uris):
    """Add tracks to a playlist"""
    try:
        if not access_token or not playlist_id or not uris:
            raise ValueError("access_token, playlist_id, and uris are required")
        
        if not isinstance(uris, list) or len(uris) == 0:
            raise ValueError("uris must be a non-empty list")
        
        # Spotify API has a limit of 100 tracks per request
        if len(uris) > 100:
            logger.warning(f"Splitting {len(uris)} tracks into multiple batches (max 100 per request)")
        
        url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        results = []
        for i in range(0, len(uris), 100):
            batch = uris[i:i+100]
            payload = {"uris": batch}
            r = requests.post(url, headers=headers, json=payload, timeout=10)
            r.raise_for_status()
            results.append(r.json())
            logger.info(f"Added {len(batch)} tracks to playlist")
        
        return results if len(results) > 1 else results[0]
    except requests.exceptions.Timeout:
        logger.error("Timeout while adding tracks to playlist")
        raise
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error adding tracks: {e.response.status_code} - {e.response.text}")
        raise
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error adding tracks: {e}")
        raise

