from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv
from token_manager import save_token, get_spotify_client, clear_token, is_token_valid
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(title="Spotify AI API", version="1.0.0")

# Configuración Spotify
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")
scope = (
    "user-read-recently-played "
    "user-top-read "
    "playlist-modify-public "
    "playlist-modify-private "
    "user-read-private "
    "user-read-email"
)

# Validate required environment variables on startup
if not all([SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI]):
    logger.error("Missing required Spotify credentials in environment variables")
    raise ValueError("SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, and SPOTIFY_REDIRECT_URI must be set")

# Login
@app.get("/login")
def login():
    """Generate Spotify authorization URL for user login"""
    try:
        auth_url = SpotifyOAuth(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
            redirect_uri=SPOTIFY_REDIRECT_URI,
            scope=scope
        ).get_authorize_url()
        
        logger.info("Login initiated - authorization URL generated")
        return JSONResponse({"auth_url": auth_url})
    except Exception as e:
        logger.error(f"Error generating auth URL: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate authorization URL: {str(e)}")

# Callback
@app.get("/callback")
def callback(request: Request):
    """Handle Spotify OAuth callback"""
    try:
        code = request.query_params.get("code")
        error = request.query_params.get("error")
        
        if error:
            logger.warning(f"OAuth error: {error}")
            error_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Authentication Error</title>
                <style>
                    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
                    .container {{ text-align: center; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 10px 25px rgba(0,0,0,0.2); max-width: 400px; }}
                    h1 {{ color: #d32f2f; margin-bottom: 10px; font-size: 28px; }}
                    p {{ color: #666; margin: 10px 0; }}
                    .error-code {{ color: #999; font-size: 14px; margin-top: 20px; background: #f5f5f5; padding: 10px; border-radius: 5px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>❌ Authentication Error</h1>
                    <p>There was a problem with Spotify authentication.</p>
                    <div class="error-code">Error: {error}</div>
                    <p>Please try logging in again.</p>
                </div>
            </body>
            </html>
            """
            return HTMLResponse(content=error_html, status_code=400)
        
        if not code:
            logger.warning("No authorization code provided in callback")
            error_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Authentication Error</title>
                <style>
                    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
                    .container {{ text-align: center; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 10px 25px rgba(0,0,0,0.2); max-width: 400px; }}
                    h1 {{ color: #d32f2f; margin-bottom: 10px; font-size: 28px; }}
                    p {{ color: #666; margin: 10px 0; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>❌ Authentication Error</h1>
                    <p>No authorization code provided.</p>
                    <p>Please try logging in again.</p>
                </div>
            </body>
            </html>
            """
            return HTMLResponse(content=error_html, status_code=400)

        sp_oauth = SpotifyOAuth(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
            redirect_uri=SPOTIFY_REDIRECT_URI,
            scope=scope
        )
        token_info = sp_oauth.get_access_token(code)
        save_token(token_info)
        
        logger.info("User authenticated successfully")
        success_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Successful</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: linear-gradient(135deg, #1DB954 0%, #1aa34a 100%); }}
                .container {{ text-align: center; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 10px 25px rgba(0,0,0,0.2); max-width: 400px; }}
                h1 {{ color: #1DB954; margin-bottom: 10px; font-size: 28px; }}
                p {{ color: #666; margin: 10px 0; line-height: 1.6; }}
                .spinner {{ border: 4px solid #f3f3f3; border-top: 4px solid #1DB954; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 20px auto; }}
                @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
                .note {{ font-size: 12px; color: #999; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>✅ Authentication Successful!</h1>
                <p>You have been authenticated with Spotify.</p>
                <div class="spinner"></div>
                <p>Closing this window in 3 seconds...</p>
                <p class="note">If the window doesn't close, you can safely close it manually.</p>
            </div>
            <script>
                // Close the window after 3 seconds
                setTimeout(function() {
                    window.close();
                }, 3000);
                // Fallback: Try to close it immediately as well (some browsers require user interaction)
                // window.close();
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=success_html)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in callback: {e}")
        raise HTTPException(status_code=500, detail=f"Authentication failed: {str(e)}")

# Crear instancia de Spotify
def spotify_client():
    """Get authenticated Spotify client"""
    sp, token_info = get_spotify_client(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI, scope)
    if not sp:
        raise HTTPException(status_code=401, detail="No valid token available. Please login first.")
    return sp

# User Profile Endpoint
@app.get("/me/profile")
def get_profile():
    """Get authenticated user's profile"""
    try:
        sp = spotify_client()
        profile = sp.current_user()
        logger.info(f"Profile fetched for user {profile.get('id')}")
        return JSONResponse({
            "id": profile.get("id"),
            "display_name": profile.get("display_name", "User"),
            "email": profile.get("email"),
            "images": profile.get("images", []),
            "external_urls": profile.get("external_urls", {}),
            "followers": profile.get("followers", {}),
            "country": profile.get("country")
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching profile: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch profile: {str(e)}")

# Logout Endpoint
@app.post("/logout")
def logout():
    """Logout user and clear tokens"""
    try:
        clear_token()
        logger.info("User logged out")
        return JSONResponse({"message": "Logged out successfully"})
    except Exception as e:
        logger.error(f"Error logging out: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to logout: {str(e)}")

# Endpoints
@app.get("/me/top-tracks")
def top_tracks(limit: int = 10):
    """Get user's top tracks from Spotify"""
    try:
        if limit < 1 or limit > 50:
            logger.warning(f"Invalid limit requested: {limit}")
            raise HTTPException(status_code=400, detail="Limit must be between 1 and 50")
        
        sp = spotify_client()
        results = sp.current_user_top_tracks(limit=limit)
        tracks = [
            {
                "name": t["name"],
                "artist": t["artists"][0]["name"] if t["artists"] else "Unknown",
                "uri": t["uri"],
                "popularity": t.get("popularity", 0)
            }
            for t in results["items"]
        ]
        logger.info(f"Retrieved {len(tracks)} top tracks")
        return JSONResponse({"top_tracks": tracks, "count": len(tracks)})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching top tracks: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch top tracks: {str(e)}")

@app.get("/me/recently-played")
def recently_played(limit: int = 10):
    """Get user's recently played tracks from Spotify"""
    try:
        if limit < 1 or limit > 50:
            logger.warning(f"Invalid limit requested: {limit}")
            raise HTTPException(status_code=400, detail="Limit must be between 1 and 50")
        
        sp = spotify_client()
        results = sp.current_user_recently_played(limit=limit)
        tracks = [
            {
                "name": t["track"]["name"],
                "artist": t["track"]["artists"][0]["name"] if t["track"]["artists"] else "Unknown",
                "uri": t["track"]["uri"],
                "played_at": t["played_at"],
                "popularity": t["track"].get("popularity", 0)
            }
            for t in results["items"]
        ]
        logger.info(f"Retrieved {len(tracks)} recently played tracks")
        return JSONResponse({"recently_played": tracks, "count": len(tracks)})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching recently played: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch recently played tracks: {str(e)}")

# Health check endpoint
@app.get("/health")
def health_check():
    """Health check endpoint"""
    return JSONResponse({"status": "ok", "service": "Spotify AI API"})

# Error handler for 404
@app.get("/")
def root():
    """Root endpoint with API information"""
    return JSONResponse({
        "name": "Spotify AI API",
        "version": "1.0.0",
        "endpoints": {
            "/login": "GET - Initiate Spotify login",
            "/callback": "GET - OAuth callback endpoint",
            "/me/top-tracks": "GET - Get user's top tracks",
            "/me/recently-played": "GET - Get user's recently played tracks",
            "/health": "GET - Health check"
        }
    })

