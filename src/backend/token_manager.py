import json
import os
from spotipy.oauth2 import SpotifyOAuth
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN_FILE = "tokens.json"

def save_token(token_info):
    """Save tokens to a local JSON file"""
    try:
        if not token_info or "access_token" not in token_info:
            raise ValueError("token_info must contain 'access_token'")
        
        with open(TOKEN_FILE, "w") as f:
            json.dump(token_info, f, indent=2)
        logger.info("Token saved successfully")
    except IOError as e:
        logger.error(f"IO error saving token: {e}")
        raise
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error saving token: {e}")
        raise

def load_token():
    """Load tokens from JSON file"""
    try:
        if not os.path.exists(TOKEN_FILE):
            logger.warning(f"Token file {TOKEN_FILE} not found")
            return None

        with open(TOKEN_FILE, "r") as f:
            token_info = json.load(f)
            logger.info("Token loaded successfully")
            return token_info
    except IOError as e:
        logger.error(f"IO error loading token: {e}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in token file: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading token: {e}")
        raise

def get_spotify_client(client_id, client_secret, redirect_uri, scope):
    """Get a Spotify client with automatic token refresh"""
    try:
        if not all([client_id, client_secret, redirect_uri, scope]):
            raise ValueError("client_id, client_secret, redirect_uri, and scope are required")
        
        token_info = load_token()

        if not token_info:
            logger.warning("No token found. User needs to authenticate first")
            return None, {"error": "No tokens found. Go to /login first."}

        oauth = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=scope
        )

        # Refresh token if expired
        if oauth.is_token_expired(token_info):
            logger.info("Token expired, refreshing...")
            token_info = oauth.refresh_access_token(token_info["refresh_token"])
            save_token(token_info)
            logger.info("Token refreshed and saved")

        from spotipy import Spotify
        sp = Spotify(auth=token_info["access_token"])
        logger.info("Spotify client created successfully")
        return sp, token_info
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return None, {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error creating Spotify client: {e}")
        return None, {"error": str(e)}

def clear_token():
    """Clear saved token (useful for logout)"""
    try:
        if os.path.exists(TOKEN_FILE):
            os.remove(TOKEN_FILE)
            logger.info("Token cleared successfully")
        else:
            logger.warning(f"Token file {TOKEN_FILE} does not exist")
    except IOError as e:
        logger.error(f"IO error clearing token: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error clearing token: {e}")
        raise

def is_token_valid():
    """Check if a valid token exists"""
    try:
        token_info = load_token()
        return token_info is not None and "access_token" in token_info
    except Exception as e:
        logger.warning(f"Error checking token validity: {e}")
        return False

