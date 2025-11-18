import streamlit as st
import requests
import os
import logging
import sys
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add backend to path for imports
backend_path = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, backend_path)

# Import database utilities
from db_utils import create_tables

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Timezone for Argentina (UTC-3)
ARGENTINA_TZ = timezone(timedelta(hours=-3))

# Configuration
FASTAPI_URL = os.getenv("FASTAPI_URL", "http://127.0.0.1:8000")
DB = os.getenv("DATABASE_URL", "sqlite:///./db.sqlite").replace("sqlite:///./", "./")

# Ensure database tables exist with proper schema
create_tables()

# Page configuration
st.set_page_config(
    page_title="Spotify AI - Mood Tagger",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main { padding-top: 2rem; }
    .mood-selector { padding: 1rem; border-radius: 0.5rem; margin: 0.5rem 0; }
    .progress-bar { margin: 1rem 0; }
    </style>
    """, unsafe_allow_html=True)

# Navigation buttons at the top
col1, col2, col3 = st.columns([2, 1, 1])
with col2:
    st.markdown("**App Navigation:**")
with col3:
    st.link_button("📊 Dashboard", "http://localhost:8501", use_container_width=True)

st.title("🎵 Spotify AI - Mood Tagger")
st.write("Help train the AI by tagging your music with moods!")

# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_info" not in st.session_state:
    st.session_state.user_info = None
if "download_status" not in st.session_state:
    st.session_state.download_status = None

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
    except Exception as e:
        logger.error(f"Error fetching profile: {e}")
    return None

def initiate_login():
    """Open Spotify login window with polling"""
    try:
        response = requests.get(f"{FASTAPI_URL}/login", timeout=10)
        if response.ok:
            auth_url = response.json().get("authorization_url")
            
            col1, col2 = st.columns([2, 1])
            with col1:
                st.info("🔗 Click the button below to log in to Spotify")
            with col2:
                st.markdown(f'<a href="{auth_url}" target="_blank"><button style="padding:10px;background-color:#1DB954;color:white;border:none;border-radius:24px;cursor:pointer;">Login with Spotify</button></a>', unsafe_allow_html=True)
            
            st.info("📍 After logging in, check back here. Polling for authentication...")
            
            # JavaScript polling
            st.markdown("""
            <script>
            let polls = 0;
            const maxPolls = 30; // 60 seconds with 2-second intervals
            const pollInterval = setInterval(() => {
                fetch('/me/profile')
                    .then(r => r.ok && location.reload())
                    .catch(() => {});
                polls++;
                if (polls >= maxPolls) clearInterval(pollInterval);
            }, 2000);
            </script>
            """, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"❌ Login failed: {e}")

def download_new_information():
    """Download new information by running ingest.py
    
    NOTE: Spotify's recently-played endpoint is limited to 50 items maximum.
    This is a Spotify API limitation, not a bug in the code.
    """
    try:
        st.info("📥 Starting data download from Spotify...")
        
        # Check if this is first time (no plays yet)
        is_first_download = False
        try:
            conn = sqlite3.connect(DB)
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM plays")
            total_plays = cur.fetchone()[0]
            conn.close()
            is_first_download = (total_plays == 0)
        except Exception as e:
            logger.warning(f"Could not check play count: {e}, assuming first download")
            is_first_download = True
        
        # Import and run ingest
        backend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")
        sys.path.insert(0, backend_path)
        from ingest import main as ingest_main
        
        # Fetch from Spotify
        if is_first_download:
            st.info("🎵 First download: Getting your recently played songs...")
            logger.info("Calling ingest with initial_download=True")
            ingest_main(initial_download=True)
        else:
            st.info("🔄 Incremental download: Getting new songs since last download...")
            logger.info("Calling ingest with initial_download=False")
            ingest_main(initial_download=False)
        
        st.session_state.download_status = "success"
        return True
        
    except Exception as e:
        logger.error(f"Error during data download: {e}")
        st.session_state.download_status = f"error: {str(e)}"
        return False

def get_untagged_plays(limit=10, offset=0):
    """Get untagged plays from database with pagination (where any tag is missing)"""
    try:
        conn = sqlite3.connect(DB)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Check if required columns exist
        cur.execute("PRAGMA table_info(plays)")
        columns = [col[1] for col in cur.fetchall()]
        
        if "mood_tag" not in columns or "mood_when_listening" not in columns or "theme_tag" not in columns:
            conn.close()
            return [], 0
        
        # Get total count of untagged plays
        cur.execute("""
            SELECT COUNT(*) FROM plays 
            WHERE mood_tag IS NULL OR mood_when_listening IS NULL OR theme_tag IS NULL
        """)
        total_count = cur.fetchone()[0]
        
        # Get plays where ANY tag is missing with pagination
        cur.execute("""
            SELECT p.id, p.track_id, p.played_at, t.track_name, t.artist, t.duration_ms, p.mood_tag, p.mood_when_listening, p.theme_tag
            FROM plays p
            JOIN tracks t ON p.track_id = t.track_id
            WHERE p.mood_tag IS NULL OR p.mood_when_listening IS NULL OR p.theme_tag IS NULL
            ORDER BY p.played_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
        
        plays = [dict(row) for row in cur.fetchall()]
        conn.close()
        return plays, total_count
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        return [], 0

def get_mood_stats():
    """Get tagging statistics (mood tags and theme tag)"""
    try:
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        
        # Check if required columns exist
        cur.execute("PRAGMA table_info(plays)")
        columns = [col[1] for col in cur.fetchall()]
        
        if "mood_tag" not in columns or "mood_when_listening" not in columns or "theme_tag" not in columns:
            conn.close()
            return {"total": 0, "tagged": 0, "untagged": 0}
        
        cur.execute("SELECT COUNT(*) FROM plays")
        total = cur.fetchone()[0]
        
        # Count plays where ALL tags are present (both moods AND theme)
        cur.execute("SELECT COUNT(*) FROM plays WHERE mood_tag IS NOT NULL AND mood_when_listening IS NOT NULL AND theme_tag IS NOT NULL")
        tagged = cur.fetchone()[0]
        
        untagged = total - tagged
        
        conn.close()
        return {"total": total, "tagged": tagged, "untagged": untagged}
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        return {"total": 0, "tagged": 0, "untagged": 0}

def get_all_table_data(table_name):
    """Get all data from a specific table"""
    try:
        conn = sqlite3.connect(DB)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        cur.execute(f"SELECT * FROM {table_name} ORDER BY rowid DESC LIMIT 1000")
        rows = [dict(row) for row in cur.fetchall()]
        conn.close()
        return rows
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        return []

def get_database_tables():
    """Get list of all tables in database"""
    try:
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cur.fetchall()]
        conn.close()
        return tables
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        return []

def detect_skipped(play_id, played_at, duration_ms):
    """Detect if a song was skipped based on time between plays and song duration.
    
    A song is considered skipped only if the next song started significantly before 
    the current song would have ended, accounting for natural gaps and pauses.
    
    Conservative approach: Only mark as skipped if gap is < 50% of song duration.
    This means the next song started before the current song was even halfway done.
    This accounts for natural pauses between songs, playlist transitions, buffer time, etc.
    
    Returns: (was_skipped: bool, skip_indicator: str)
    """
    try:
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        
        # Get the next play after this one
        cur.execute("""
            SELECT played_at FROM plays 
            WHERE played_at > ?
            ORDER BY played_at ASC
            LIMIT 1
        """, (played_at,))
        
        result = cur.fetchone()
        conn.close()
        
        if not result:
            # No next song recorded, can't determine if skipped
            return False, "⏸️ (unknown)"
        
        next_played_at = result[0]
        
        # Parse timestamps (ISO format from Spotify)
        from datetime import datetime
        current_time = datetime.fromisoformat(played_at.replace('Z', '+00:00'))
        next_time = datetime.fromisoformat(next_played_at.replace('Z', '+00:00'))
        
        # Calculate time between songs in seconds
        time_between = (next_time - current_time).total_seconds()
        
        # Duration is in milliseconds
        song_duration_seconds = (duration_ms / 1000) if duration_ms else 0
        
        # Only mark as skipped if next song started before 50% of current song was played
        # This is much more conservative and accounts for:
        # - Natural pauses between songs (1-5 seconds)
        # - Playlist transitions
        # - Buffer/loading time
        skip_threshold = song_duration_seconds * 0.5
        
        if time_between < skip_threshold:
            return True, "⏭️ (skipped)"
        else:
            return False, "✅ (played)"
            
    except Exception as e:
        logger.warning(f"Could not determine skip status: {e}")
        return False, "❓ (unknown)"

# Check authentication on every page load
if not st.session_state.authenticated:
    if check_token_validity():
        st.session_state.authenticated = True
        st.session_state.user_info = fetch_user_profile()
    else:
        st.warning("⚠️ Not authenticated. Please log in to continue.")
        initiate_login()
        st.stop()

# Authenticated content
with st.sidebar:
    st.header("👤 User Info")
    if st.session_state.user_info:
        user = st.session_state.user_info
        if user.get("images") and len(user.get("images", [])) > 0:
            st.image(user["images"][0]["url"], width=150)
        st.write(f"**Name:** {user.get('display_name', 'Unknown')}")
        st.write(f"**Email:** {user.get('email', 'N/A')}")
        st.write(f"**Followers:** {user.get('followers', {}).get('total', 0):,}")
        
        if st.button("🚪 Logout", use_container_width=True):
            requests.post(f"{FASTAPI_URL}/logout")
            st.session_state.authenticated = False
            st.session_state.user_info = None
            st.rerun()

# Main content
st.markdown("---")

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs(["🎵 Mood Tagging", "📊 Database Viewer", "📥 Data Management", "📋 Tagged Songs"])

# TAB 1: Mood Tagging
with tab1:
    st.subheader("Tag Your Music")
    st.write("Rate songs with a mood score to help train the AI:")

    # Statistics section
    st.subheader("📊 Tagging Progress")
    stats = get_mood_stats()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Plays", stats["total"])
    with col2:
        st.metric("Tagged", stats["tagged"], delta=f"{(stats['tagged']/max(stats['total'],1)*100):.1f}%")
    with col3:
        st.metric("Untagged", stats["untagged"])

    if stats["total"] > 0:
        progress = stats["tagged"] / stats["total"]
        st.progress(progress, text=f"{progress*100:.1f}% Complete")

    st.markdown("---")

    # Tagging interface with pagination
    untagged, total_untagged = get_untagged_plays(limit=10, offset=0)
    
    # Initialize pagination in session state
    if "tagging_page" not in st.session_state:
        st.session_state.tagging_page = 0
    
    items_per_page = 10
    total_pages = (total_untagged + items_per_page - 1) // items_per_page if total_untagged > 0 else 0

    if total_untagged == 0:
        if stats["total"] == 0:
            st.info("💾 No plays in database yet. Go to 'Data Management' tab and click 'Download New Information' to get started!")
        else:
            st.success("🎉 You've tagged all your plays! Great job! 🎵")
    else:
        st.info(f"📝 You have {stats['untagged']} untagged plays. Tag the song mood, your mood, and theme!")
        st.markdown("""
        **Three-tag system:**
        - **🎵 Song Mood**: How does this song sound?
        - **👤 Your Mood**: How were YOU feeling?
        - **🎭 Theme**: The vibe/context (romantic, nostalgic, energetic, etc.)
        """)
        
        # Pagination controls
        st.markdown("---")
        col_page, col_nav = st.columns([2, 3])
        with col_page:
            st.write(f"**Page {st.session_state.tagging_page + 1} of {max(1, total_pages)}** | Showing {min(items_per_page, total_untagged - st.session_state.tagging_page * items_per_page)} of {total_untagged} untagged")
        
        with col_nav:
            nav_col1, nav_col2, nav_col3 = st.columns([1, 1, 1])
            with nav_col1:
                if st.button("⬅️ Previous", disabled=(st.session_state.tagging_page == 0), use_container_width=True):
                    st.session_state.tagging_page -= 1
                    st.rerun()
            with nav_col3:
                if st.button("Next ➡️", disabled=(st.session_state.tagging_page >= total_pages - 1), use_container_width=True):
                    st.session_state.tagging_page += 1
                    st.rerun()
        
        st.markdown("---")
        
        # Get current page data
        offset = st.session_state.tagging_page * items_per_page
        untagged, _ = get_untagged_plays(limit=items_per_page, offset=offset)
        
        # Display untagged plays for tagging
        mood_scale = ["😢 Very Sad", "😕 Sad", "😐 Neutral", "😊 Happy", "🤩 Very Happy"]
        mood_values = {"😢 Very Sad": 1, "😕 Sad": 2, "😐 Neutral": 3, "😊 Happy": 4, "🤩 Very Happy": 5}
        
        theme_options = ["🎭 Romantic", "🎭 Nostalgic", "🎭 Energetic", "🎭 Chill/Relaxing", "🎭 Dark/Moody", "🎭 Uplifting", "🎭 Melancholic", "🎭 Playful", "🎭 Party", "🎭 Introspective"]
        
        for i, play in enumerate(untagged):
            with st.container(border=True):
                # Detect if song was skipped
                was_skipped, skip_indicator = detect_skipped(play['id'], play['played_at'], play['duration_ms'])
                
                # Header with song info
                st.write(f"**{play['track_name']}** {skip_indicator}")
                st.write(f"*{play['artist']}*")
                try:
                    from datetime import datetime as dt
                    played_time = dt.fromisoformat(play['played_at'].replace('Z', '+00:00')).strftime("%Y-%m-%d %H:%M")
                    st.caption(f"🕐 Played: {played_time}")
                except:
                    st.caption(f"🕐 Played: {play['played_at'][:16]}")
                
                st.markdown("---")
                
                # Three-column tagging interface
                col_song, col_listen, col_theme = st.columns(3)
                
                with col_song:
                    st.markdown("### 🎵 Song Mood")
                    st.write("*How does this song sound?*")
                    song_mood = st.radio(
                        "Song mood:",
                        mood_scale,
                        key=f"song_mood_{play['id']}_{st.session_state.tagging_page}",
                        horizontal=False,
                        label_visibility="collapsed"
                    )
                    song_mood_value = mood_values.get(song_mood, 3)
                
                with col_listen:
                    st.markdown("### 👤 Your Mood")
                    st.write("*How did you feel?*")
                    listening_mood = st.radio(
                        "Your mood when listening:",
                        mood_scale,
                        key=f"listen_mood_{play['id']}_{st.session_state.tagging_page}",
                        horizontal=False,
                        label_visibility="collapsed"
                    )
                    listening_mood_value = mood_values.get(listening_mood, 3)
                
                with col_theme:
                    st.markdown("### 🎭 Theme")
                    st.write("*Vibe/Context?*")
                    theme = st.selectbox(
                        "Theme:",
                        theme_options,
                        key=f"theme_{play['id']}_{st.session_state.tagging_page}",
                        label_visibility="collapsed"
                    )
                    # Extract theme name (remove emoji)
                    theme_value = theme.split(" ", 1)[1] if " " in theme else theme
                
                # Save button
                if st.button("💾 Save All Tags", key=f"save_{play['id']}_{st.session_state.tagging_page}", use_container_width=True):
                    try:
                        conn = sqlite3.connect(DB)
                        cur = conn.cursor()
                        # Convert boolean to 0/1 for SQLite
                        skip_value = 1 if was_skipped else 0
                        # Use Argentina timezone (UTC-3)
                        tagged_time = datetime.now(ARGENTINA_TZ).isoformat()
                        cur.execute(
                            "UPDATE plays SET mood_tag = ?, mood_when_listening = ?, theme_tag = ?, is_skipped = ?, tagged_at = ? WHERE id = ?",
                            (song_mood_value, listening_mood_value, theme_value, skip_value, tagged_time, play['id'])
                        )
                        conn.commit()
                        conn.close()
                        st.success(f"✅ Tagged! Song: {song_mood} | You: {listening_mood} | Theme: {theme_value} | {skip_indicator}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error saving tags: {e}")

    st.caption("💡 Tip: Download new information frequently to keep your dataset fresh and growing!")

# TAB 2: Database Viewer
with tab2:
    st.subheader("📊 Database Viewer")
    st.write("View all data stored in your local database")
    
    # Get available tables
    tables = get_database_tables()
    
    if not tables:
        st.warning("No tables found in database")
    else:
        # Table selector
        selected_table = st.selectbox("Select table to view:", tables, key="table_selector")
        
        if selected_table:
            # Get table data
            data = get_all_table_data(selected_table)
            
            if not data:
                st.info(f"No data in '{selected_table}' table yet")
            else:
                # Display statistics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Rows", len(data))
                with col2:
                    # Count columns
                    num_cols = len(data[0].keys()) if data else 0
                    st.metric("Columns", num_cols)
                with col3:
                    st.metric("Displaying", f"Last 1000 rows")
                
                st.markdown("---")
                
                # Display data in an expandable format with search
                col1, col2 = st.columns([3, 1])
                with col1:
                    search_query = st.text_input("🔍 Search in data (partial match):", "")
                with col2:
                    export_csv = st.checkbox("📥 Show as CSV", value=False)
                
                # Filter data if search query provided
                if search_query:
                    filtered_data = []
                    for row in data:
                        if any(search_query.lower() in str(v).lower() for v in row.values()):
                            filtered_data.append(row)
                    display_data = filtered_data
                    st.caption(f"Found {len(filtered_data)} matching rows")
                else:
                    display_data = data
                
                if export_csv:
                    # Convert to pandas for nice CSV export
                    import pandas as pd
                    df = pd.DataFrame(display_data)
                    st.dataframe(df, use_container_width=True)
                    
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download as CSV",
                        data=csv,
                        file_name=f"{selected_table}_export.csv",
                        mime="text/csv"
                    )
                else:
                    # Display as scrollable table
                    if display_data:
                        import pandas as pd
                        df = pd.DataFrame(display_data)
                        st.dataframe(df, use_container_width=True, height=600)
                    else:
                        st.info("No matching results")

# TAB 3: Data Management
with tab3:
    st.subheader("📥 Download New Information")
    st.write("Fetch your latest listening history from Spotify. This will:")
    st.write("- Get all tracks you've listened to (paginated from Spotify API)")
    st.write("- Store them in the local database")
    st.write("- Fetch audio features for each track")

    col1, col2 = st.columns([3, 1])
    with col1:
        if st.button("🔄 Download New Information", use_container_width=True, type="primary"):
            with st.spinner("⏳ Downloading your music history... This may take a few minutes depending on how much you've listened."):
                if download_new_information():
                    st.success("✅ Download complete! Your music history has been updated.")
                    st.rerun()
                else:
                    st.error(f"❌ Download failed: {st.session_state.download_status}")

# TAB 4: Tagged Songs
with tab4:
    st.subheader("📋 All Tagged Songs")
    st.write("View all songs you've tagged with their listening and tagging timestamps (UTC-3 Argentina time)")
    
    try:
        conn = sqlite3.connect(DB)
        cur = conn.cursor()
        
        # Get all tagged songs with track info
        cur.execute("""
            SELECT 
                p.id,
                t.track_name,
                t.artist,
                p.played_at,
                p.tagged_at,
                CASE 
                    WHEN p.mood_tag = 1 THEN '😢 Very Sad'
                    WHEN p.mood_tag = 2 THEN '😕 Sad'
                    WHEN p.mood_tag = 3 THEN '😐 Neutral'
                    WHEN p.mood_tag = 4 THEN '🙂 Happy'
                    WHEN p.mood_tag = 5 THEN '😄 Very Happy'
                    ELSE '❓ Not Tagged'
                END as song_mood,
                CASE 
                    WHEN p.mood_when_listening = 1 THEN '😢 Very Sad'
                    WHEN p.mood_when_listening = 2 THEN '😕 Sad'
                    WHEN p.mood_when_listening = 3 THEN '😐 Neutral'
                    WHEN p.mood_when_listening = 4 THEN '🙂 Happy'
                    WHEN p.mood_when_listening = 5 THEN '😄 Very Happy'
                    ELSE '❓ Not Tagged'
                END as listening_mood,
                p.theme_tag,
                CASE 
                    WHEN p.is_skipped = 1 THEN '⏭️ Skipped'
                    WHEN p.is_skipped = 0 THEN '✅ Completed'
                    ELSE '❓ Unknown'
                END as play_status
            FROM plays p
            JOIN tracks t ON p.track_id = t.track_id
            WHERE p.mood_tag IS NOT NULL OR p.mood_when_listening IS NOT NULL OR p.theme_tag IS NOT NULL
            ORDER BY p.played_at DESC
        """)
        
        raw_songs = cur.fetchall()
        conn.close()
        
        # Convert timestamps to UTC-3
        def convert_timestamp(ts_str):
            """Convert UTC timestamp to UTC-3 (Argentina)"""
            if not ts_str:
                return "N/A"
            try:
                if 'T' in ts_str and '+' not in ts_str and 'Z' not in ts_str:
                    # Already in local time
                    return ts_str[:19]  # Return without microseconds
                # Convert from UTC to UTC-3
                dt_utc = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                dt_arg = dt_utc.astimezone(ARGENTINA_TZ)
                return dt_arg.strftime("%Y-%m-%d %H:%M:%S")
            except:
                return ts_str[:19] if ts_str else "N/A"
        
        # Transform data with converted timestamps
        tagged_songs = []
        for song in raw_songs:
            played_converted = convert_timestamp(song[3])
            tagged_converted = convert_timestamp(song[4])
            tagged_songs.append((
                song[0], song[1], song[2],  # id, track, artist
                played_converted, tagged_converted,  # converted timestamps
                song[5], song[6], song[7], song[8]  # moods, theme, status
            ))
        
        if tagged_songs:
            # Display statistics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Tagged", len(tagged_songs))
            with col2:
                skipped_count = sum(1 for song in tagged_songs if song[8] == '⏭️ Skipped')
                st.metric("Skipped", skipped_count)
            with col3:
                completed_count = sum(1 for song in tagged_songs if song[8] == '✅ Completed')
                st.metric("Completed", completed_count)
            
            st.markdown("---")
            
            # Display options
            col1, col2 = st.columns([3, 1])
            with col1:
                search_query = st.text_input("🔍 Search songs (artist or title):", "")
            with col2:
                show_csv = st.checkbox("📥 Export as CSV", value=False)
            
            # Filter data if search query provided
            filtered_songs = tagged_songs
            if search_query:
                filtered_songs = [
                    song for song in tagged_songs 
                    if search_query.lower() in song[1].lower() or search_query.lower() in song[2].lower()
                ]
                st.caption(f"Found {len(filtered_songs)} matching songs")
            
            if show_csv:
                # Convert to DataFrame for CSV export
                import pandas as pd
                df = pd.DataFrame(
                    filtered_songs,
                    columns=["ID", "Track", "Artist", "Listened At", "Tagged At", "Song Mood", "Your Mood", "Theme", "Play Status"]
                )
                st.dataframe(df, use_container_width=True)
                
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Download as CSV",
                    data=csv,
                    file_name="tagged_songs_export.csv",
                    mime="text/csv"
                )
            else:
                # Display as interactive table
                import pandas as pd
                df = pd.DataFrame(
                    filtered_songs,
                    columns=["ID", "Track", "Artist", "Listened At", "Tagged At", "Song Mood", "Your Mood", "Theme", "Play Status"]
                )
                
                # Format the dataframe for better display
                st.dataframe(
                    df,
                    use_container_width=True,
                    height=600,
                    column_config={
                        "Listened At": st.column_config.TextColumn(width="medium"),
                        "Tagged At": st.column_config.TextColumn(width="medium"),
                        "Track": st.column_config.TextColumn(width="large"),
                        "Artist": st.column_config.TextColumn(width="medium"),
                    }
                )
        else:
            st.info("📭 No tagged songs yet. Start tagging in the 'Mood Tagging' tab!")
    
    except Exception as e:
        st.error(f"Error loading tagged songs: {e}")
