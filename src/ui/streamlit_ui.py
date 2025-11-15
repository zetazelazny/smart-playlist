import streamlit as st
import requests
import os
import logging
from datetime import datetime
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
FASTAPI_URL = os.getenv("FASTAPI_URL", "http://127.0.0.1:8000")
TOKEN_CHECK_INTERVAL = 2  # seconds

# Page configuration
st.set_page_config(
    page_title="Spotify AI",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom styling
st.markdown("""
    <style>
    .main { padding-top: 2rem; }
    .stMetric { background-color: #f0f2f6; padding: 1rem; border-radius: 0.5rem; }
    .auth-container { padding: 2rem; text-align: center; }
    .nav-button { display: inline-block; margin: 0.5rem; }
    </style>
    """, unsafe_allow_html=True)

# Navigation buttons at the top
col1, col2, col3 = st.columns([2, 1, 1])
with col2:
    st.markdown("**App Navigation:**")
with col3:
    st.link_button("🎯 Mood Tagger", "http://localhost:8502", use_container_width=True)

st.title("🎵 Spotify AI - Your Music Intelligence Dashboard")

# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_info" not in st.session_state:
    st.session_state.user_info = None
if "checking_token" not in st.session_state:
    st.session_state.checking_token = False

def check_token_validity():
    """Check if a valid token exists by testing API"""
    try:
        response = requests.get(f"{FASTAPI_URL}/me/profile", timeout=5)
        return response.ok
    except Exception:
        return False

def fetch_user_profile():
    """Fetch user profile from API"""
    try:
        response = requests.get(f"{FASTAPI_URL}/me/profile", timeout=10)
        if response.ok:
            return response.json()
        return None
    except Exception as e:
        logger.error(f"Error fetching profile: {e}")
        return None

def initiate_login():
    """Initiate Spotify OAuth login"""
    try:
        response = requests.get(f"{FASTAPI_URL}/login", timeout=10)
        if response.ok:
            auth_url = response.json()["auth_url"]
            logger.info("Authorization URL generated")
            
            # Open auth URL in new window
            js = f"""
            <script>
                window.open('{auth_url}', 'spotify_auth', 'width=500,height=700');
                // Check for token every 2 seconds for up to 60 seconds
                let attempts = 0;
                let checkInterval = setInterval(function() {{
                    attempts++;
                    fetch('{FASTAPI_URL}/me/profile')
                        .then(r => r.ok ? clearInterval(checkInterval) : null)
                        .catch(() => null);
                    if (attempts > 30) clearInterval(checkInterval);
                }}, 2000);
            </script>
            """
            st.components.v1.html(js, height=0)
            return True
        return False
    except Exception as e:
        logger.error(f"Error initiating login: {e}")
        return False

# Main app logic
def main():
    # Check token validity on every load
    if not st.session_state.authenticated:
        if check_token_validity():
            st.session_state.authenticated = True
            user_info = fetch_user_profile()
            if user_info:
                st.session_state.user_info = user_info
                logger.info(f"User authenticated: {user_info.get('display_name', 'Unknown')}")

    # Sidebar authentication
    with st.sidebar:
        st.header("🔐 Authentication")
        
        if st.session_state.authenticated and st.session_state.user_info:
            user = st.session_state.user_info
            
            # Display user info
            st.success(f"✅ Logged in as **{user.get('display_name', 'User')}**")
            st.caption(f"📧 {user.get('email', 'No email')}")
            
            if user.get('images') and len(user['images']) > 0:
                st.image(user['images'][0]['url'], width=100)
            
            st.divider()
            
            # Logout button
            if st.button("🚪 Logout", use_container_width=True):
                try:
                    response = requests.post(f"{FASTAPI_URL}/logout", timeout=10)
                    st.session_state.authenticated = False
                    st.session_state.user_info = None
                    logger.info("User logged out")
                    st.success("Logged out successfully")
                    st.rerun()
                except Exception as e:
                    logger.error(f"Error logging out: {e}")
                    st.error(f"Error logging out: {str(e)}")
        else:
            st.info("""
            👋 Welcome to **Spotify AI**!
            
            This application learns your music preferences and helps you discover the perfect playlist for any mood or moment.
            """)
            
            if st.button("🔗 Login with Spotify", key="login_btn", use_container_width=True):
                with st.spinner("Opening Spotify login..."):
                    if initiate_login():
                        st.info("✅ Spotify login window opened. Please complete authentication and this page will refresh automatically.")
                        # Wait and check for token
                        for i in range(30):  # Check for up to 60 seconds
                            time.sleep(2)
                            if check_token_validity():
                                logger.info("Token detected, refreshing page...")
                                st.success("✅ Authentication successful! Loading your profile...")
                                st.rerun()
                                break
                    else:
                        st.error("Failed to generate login URL. Please check your configuration.")

    # Main content area
    if st.session_state.authenticated and st.session_state.user_info:
        user = st.session_state.user_info
        
        # User welcome section
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown(f"### Welcome, {user.get('display_name', 'Music Lover')}! 🎧")
        
        st.divider()
        
        # Main content tabs
        tab1, tab2, tab3 = st.tabs(["🔥 Top Tracks", "🎧 Recently Played", "🎼 Playlists"])
        
        with tab1:
            st.subheader("Your Top Tracks")
            col1, col2 = st.columns([1, 3])
            with col1:
                limit = st.slider("Number of tracks", 1, 50, 20, key="top_limit")
            
            if st.button("📥 Load Top Tracks", use_container_width=True, key="load_top"):
                try:
                    with st.spinner("Loading your top tracks..."):
                        res = requests.get(f"{FASTAPI_URL}/me/top-tracks?limit={limit}", timeout=10)
                        if res.ok:
                            data = res.json()
                            tracks = data.get("top_tracks", [])
                            count = data.get("count", 0)
                            
                            if tracks:
                                st.success(f"✅ Loaded {count} top tracks")
                                
                                # Display as a nice table-like format
                                for idx, track in enumerate(tracks, start=1):
                                    with st.container():
                                        col_num, col_info = st.columns([0.8, 4])
                                        with col_num:
                                            st.markdown(f"**#{idx}**")
                                        with col_info:
                                            st.markdown(f"**{track['name']}**")
                                            st.caption(f"{track['artist']} • Popularity: {track.get('popularity', 'N/A')}")
                                        st.divider()
                            else:
                                st.warning("No top tracks found")
                        else:
                            logger.error(f"Failed to load: {res.text}")
                            st.error(f"Failed to load top tracks")
                except requests.exceptions.Timeout:
                    logger.error("Timeout loading top tracks")
                    st.error("❌ Request timeout. Is the API server running?")
                except Exception as e:
                    logger.error(f"Error: {e}")
                    st.error(f"❌ Error: {str(e)}")
        
        with tab2:
            st.subheader("Recently Played")
            col1, col2 = st.columns([1, 3])
            with col1:
                limit = st.slider("Number of tracks", 1, 50, 20, key="recent_limit")
            
            if st.button("📥 Load Recently Played", use_container_width=True, key="load_recent"):
                try:
                    with st.spinner("Loading recently played tracks..."):
                        res = requests.get(f"{FASTAPI_URL}/me/recently-played?limit={limit}", timeout=10)
                        if res.ok:
                            data = res.json()
                            tracks = data.get("recently_played", [])
                            count = data.get("count", 0)
                            
                            if tracks:
                                st.success(f"✅ Loaded {count} recently played tracks")
                                
                                for idx, track in enumerate(tracks, start=1):
                                    with st.container():
                                        col_num, col_info = st.columns([0.8, 4])
                                        with col_num:
                                            st.markdown(f"**#{idx}**")
                                        with col_info:
                                            st.markdown(f"**{track['name']}**")
                                            played_at = track.get('played_at', 'N/A')
                                            st.caption(f"{track['artist']} • {played_at}")
                                        st.divider()
                            else:
                                st.warning("No recently played tracks found")
                        else:
                            logger.error(f"Failed to load: {res.text}")
                            st.error(f"Failed to load recently played tracks")
                except requests.exceptions.Timeout:
                    logger.error("Timeout loading recently played")
                    st.error("❌ Request timeout. Is the API server running?")
                except Exception as e:
                    logger.error(f"Error: {e}")
                    st.error(f"❌ Error: {str(e)}")
        
        with tab3:
            st.info("🚧 Playlist features coming soon...")
        
        # System status
        st.divider()
        st.subheader("🏥 System Status")
        try:
            res = requests.get(f"{FASTAPI_URL}/health", timeout=5)
            if res.ok:
                st.success("✅ API Server: Online")
            else:
                st.error("❌ API Server: Unreachable")
        except Exception:
            st.error("❌ API Server: Unreachable")
    else:
        # Not authenticated - show welcome screen
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            ### 🎵 Welcome to Spotify AI
            
            **Your AI-Powered Music Discovery Platform**
            
            This intelligent agent learns your music preferences to create the perfect playlists for any mood or moment.
            
            ---
            
            #### Features:
            - 📊 Analyze your listening patterns
            - 🤖 AI-powered playlist generation
            - 🎧 Mood-based recommendations
            - 📈 Track your musical taste evolution
            - 🎯 Discover new music you'll love
            
            #### Getting Started:
            1. Click **"Login with Spotify"** in the sidebar
            2. Authorize the application
            3. Explore your music data
            
            """)
            
            st.divider()
            st.caption("🔒 Your data is private and secure")

if __name__ == "__main__":
    main()
