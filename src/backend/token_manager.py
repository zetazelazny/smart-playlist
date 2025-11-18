import json
import os
from spotipy.oauth2 import SpotifyOAuth
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _get_token_paths():
    """Return list of possible token file paths in priority order"""
    # Try to get the backend directory path
    try:
        # First try: use __file__ relative to this module
        script_file = os.path.abspath(__file__)
        script_dir = os.path.dirname(script_file)
        logger.info(f"DEBUG: __file__ resolved to {script_file}")
    except:
        # Fallback: use current working directory
        script_dir = os.getcwd()
        logger.info(f"DEBUG: __file__ failed, using cwd: {script_dir}")
    
    # Navigate up to root
    root_dir = script_dir
    for _ in range(3):  # Go up max 3 levels
        if os.path.exists(os.path.join(root_dir, "src", "backend")):
            break
        if os.path.exists(os.path.join(root_dir, ".git")):
            break
        root_dir = os.path.dirname(root_dir)
    
    paths = [
        os.path.join(script_dir, "tokens.json"),  # Direct: src/backend/tokens.json
        os.path.join(root_dir, "data", "tokens.json"),  # root/data/tokens.json
        os.path.join(root_dir, "src", "backend", "tokens.json"),  # Explicit path
        "tokens.json",  # current working directory
    ]
    logger.info(f"DEBUG _get_token_paths: Checking paths in order:")
    for p in paths:
        logger.info(f"  - {os.path.abspath(p)}")
    return paths

def _find_token_file():
    """Find the token file in any of the expected locations"""
    paths = _get_token_paths()
    logger.info(f"Looking for token file in: {paths}")
    for path in paths:
        logger.info(f"Checking: {os.path.abspath(path)}")
        if os.path.exists(path):
            logger.info(f"✓ Found token file at: {os.path.abspath(path)}")
            return path
    logger.error(f"✗ Token file not found in any location: {paths}")
    return None

def save_token(token_info):
    """Save tokens to a local JSON file"""
    try:
        if not token_info or "access_token" not in token_info:
            raise ValueError("token_info must contain 'access_token'")
        
        # Save to backend directory primarily
        token_file = _get_token_paths()[0]
        os.makedirs(os.path.dirname(token_file), exist_ok=True)
        
        with open(token_file, "w") as f:
            json.dump(token_info, f, indent=2)
        logger.info(f"Token saved successfully to {os.path.abspath(token_file)}")
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
    """Load tokens from JSON file, checking multiple locations"""
    try:
        token_file = _find_token_file()
        if not token_file:
            logger.warning(f"Token file not found. Checked paths: {_get_token_paths()}")
            return None

        with open(token_file, "r") as f:
            token_info = json.load(f)
            logger.info(f"Token loaded successfully from {os.path.abspath(token_file)}")
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
        token_file = _find_token_file()
        if token_file and os.path.exists(token_file):
            os.remove(token_file)
            logger.info(f"Token cleared successfully from {token_file}")
        else:
            logger.warning(f"Token file not found to clear")
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

