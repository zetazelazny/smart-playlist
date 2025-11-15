import os, requests
from urllib.parse import urlencode
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")
SCOPES = "user-read-recently-played user-top-read playlist-modify-public playlist-modify-private user-library-read"

# Validate required environment variables
if not all([CLIENT_ID, CLIENT_SECRET, REDIRECT_URI]):
    logger.error("Missing required Spotify credentials in environment variables")
    raise ValueError("SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, and SPOTIFY_REDIRECT_URI must be set")

def make_authorize_url():
    """Generate Spotify authorization URL"""
    try:
        params = {
            "client_id": CLIENT_ID,
            "response_type": "code",
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPES,
            "show_dialog": "true"
        }
        url = f"https://accounts.spotify.com/authorize?{urlencode(params)}"
        logger.info("Authorization URL generated successfully")
        return url
    except Exception as e:
        logger.error(f"Error generating authorization URL: {e}")
        raise

def exchange_code_for_token(code):
    """Exchange authorization code for access and refresh tokens"""
    try:
        if not code:
            raise ValueError("Authorization code cannot be empty")
        
        url = "https://accounts.spotify.com/api/token"
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET
        }
        r = requests.post(url, data=data, timeout=10)
        r.raise_for_status()
        logger.info("Authorization code exchanged for token successfully")
        return r.json()
    except requests.exceptions.Timeout:
        logger.error("Timeout while exchanging authorization code")
        raise
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error exchanging code: {e.response.status_code} - {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"Error exchanging authorization code: {e}")
        raise

def refresh_access_token(refresh_token):
    """Refresh access token using refresh token"""
    try:
        if not refresh_token:
            raise ValueError("Refresh token cannot be empty")
        
        url = "https://accounts.spotify.com/api/token"
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET
        }
        r = requests.post(url, data=data, timeout=10)
        r.raise_for_status()
        logger.info("Access token refreshed successfully")
        return r.json()
    except requests.exceptions.Timeout:
        logger.error("Timeout while refreshing access token")
        raise
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error refreshing token: {e.response.status_code} - {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"Error refreshing access token: {e}")
        raise

def get_user_profile(access_token):
    """Fetch user profile information from Spotify"""
    try:
        if not access_token:
            raise ValueError("Access token cannot be empty")
        
        headers = {"Authorization": f"Bearer {access_token}"}
        r = requests.get("https://api.spotify.com/v1/me", headers=headers, timeout=10)
        r.raise_for_status()
        logger.info("User profile retrieved successfully")
        return r.json()
    except requests.exceptions.Timeout:
        logger.error("Timeout while fetching user profile")
        raise
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error fetching profile: {e.response.status_code} - {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"Error fetching user profile: {e}")
        raise
