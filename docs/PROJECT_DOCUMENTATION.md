# Spotify AI - Mood-Based Playlist Generator
## Complete Project Documentation & Progress Report

---

## 📋 Executive Summary

**Spotify AI** is a mood-based music recommendation system that analyzes your listening history and tags songs with two distinct moods:
1. **Song Mood**: How the song sounds (intrinsic audio characteristics)
2. **Your Mood**: How you felt when listening (contextual listener state)

The system collects play history via Spotify API, stores it locally in SQLite, allows manual mood tagging, and provides a foundation for building an ML-powered mood-based playlist generator.

**Current Status**: ✅ Core MVP complete and functional

---

## 🎯 Key Features

### Authentication & Authorization
- ✅ Secure Spotify OAuth2 login (no manual token management)
- ✅ Automatic token refresh without user intervention
- ✅ Profile fetching and user information display
- ✅ Session persistence via tokens.json

### Data Collection
- ✅ Downloads recently played tracks from Spotify (50 max - API limitation)
- ✅ Fetches audio features (energy, danceability, valence, tempo) in batches
- ✅ Full datetime storage with timezone support
- ✅ Incremental updates (skips duplicates, adds new plays)
- ✅ Download history tracking for auditing

### Database
- ✅ SQLite with 4 synchronized tables:
  - `users` - Profile information
  - `tracks` - Song metadata + computed audio features
  - `plays` - Complete listening history with mood tags
  - `download_history` - Incremental update tracking

### Mood Tagging Interface
- ✅ **Tab 1 - Mood Tagging**:
  - Shows 10 untagged plays at a time
  - Two-mood system: Song Mood | Your Mood (side-by-side selection)
  - 5-point scale (Very Sad → Very Happy) for both moods
  - Full datetime display of when played
  - Single button save (updates both moods atomically)
  - Progress tracking (X of Y tagged)

- ✅ **Tab 2 - Database Viewer**:
  - Browse any database table
  - Search functionality (partial match across all fields)
  - CSV export for external analysis
  - Column sorting and filtering
  - Shows row counts and metadata

- ✅ **Tab 3 - Data Management**:
  - "Download New Information" button
  - Auto-detects first vs incremental downloads
  - Status messages and error handling
  - Prevents duplicate plays

### Navigation
- ✅ Buttons to switch between dashboards
- ✅ User profile display with Spotify image
- ✅ Logout functionality
- ✅ Error handling with helpful messages

### Developer Tools
- ✅ Comprehensive logging in all modules
- ✅ Debug output for troubleshooting
- ✅ Reproducible test scripts (created during development, can be removed)

---

## ⚙️ Technical Stack

**Backend**
- Python 3.8+
- FastAPI 0.95+ (OAuth endpoints, API routes)
- Spotipy 2.22+ (Spotify Web API wrapper)

**Frontend**
- Streamlit 1.32.2 (Two separate apps: main dashboard + mood tagger)

**Database**
- SQLite 3 (local file-based storage)

**Key Libraries**
- requests (HTTP client)
- pandas (data manipulation & CSV export)
- python-dotenv (environment configuration)

---

## 📁 Project Structure

### Core Application Files (Production)

```
app.py                      # FastAPI backend with OAuth & API endpoints
auth_helpers.py            # Spotify OAuth token management & refresh
token_manager.py           # Token persistence (tokens.json)
db_utils.py                # Database schema & utility functions
ingest.py                  # Downloads Spotify data & stores in DB
spotify_ops.py             # Playlist creation & track management
streamlit_tag.py           # Main UI: Mood tagging, DB viewer, downloads
streamlit_ui.py            # Legacy dashboard (top tracks, recently played)
```

### Configuration Files

```
.env                       # Environment variables (CLIENT_ID, CLIENT_SECRET, REDIRECT_URI)
.env.example              # Template for .env
requirements.txt          # Python dependencies
Dockerfile                # Optional container deployment
tokens.json               # Persistent Spotify tokens (auto-created)
db.sqlite                 # SQLite database (auto-created)
```

### Documentation Files (Consolidated)

```
PROJECT_DOCUMENTATION.md  # THIS FILE - Complete reference
README.md                 # Quick start guide
QUICK_START.md           # Step-by-step setup instructions
```

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.8+
- Spotify Developer account (free at https://developer.spotify.com)
- pip (Python package manager)

### Setup Steps

1. **Clone/Navigate to project**:
   ```bash
   cd "c:\Users\matiz\OneDrive\Escritorio\Spotiffy IA"
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate  # Windows
   # source .venv/bin/activate  # macOS/Linux
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Spotify credentials**:
   - Copy `.env.example` to `.env`
   - Add your Spotify Developer credentials:
     - `SPOTIFY_CLIENT_ID=your_client_id`
     - `SPOTIFY_CLIENT_SECRET=your_client_secret`
     - `REDIRECT_URI=http://localhost:8000/auth/callback`

5. **Start the backend** (Terminal 1):
   ```bash
   uvicorn app:app --reload --port 8000
   ```

6. **Start the mood tagger UI** (Terminal 2):
   ```bash
   streamlit run streamlit_tag.py
   ```

7. **Log in via Spotify OAuth** when prompted

8. **Download your first 50 plays** using the Data Management tab

9. **Start tagging** plays with both song mood and your mood

### Running the Legacy Dashboard
```bash
streamlit run streamlit_ui.py
```

---

## 📊 Data Model

### Database Tables

#### `users` Table
```sql
user_id TEXT PRIMARY KEY        -- Spotify user ID
display_name TEXT               -- Spotify display name
email TEXT                      -- User email
created_at DATETIME             -- Record creation timestamp
```

#### `tracks` Table
```sql
track_id TEXT PRIMARY KEY       -- Spotify track ID
track_name TEXT                 -- Song title
artist TEXT                     -- Artist name(s)
duration_ms INTEGER             -- Track length in milliseconds
popularity INTEGER              -- Spotify popularity (0-100)
genre TEXT                      -- Music genre
energy REAL                     -- Energy level (0-1) from audio features
danceability REAL               -- Danceability (0-1) from audio features
valence REAL                    -- Positivity (0-1) from audio features
tempo REAL                      -- BPM from audio features
mood TEXT                       -- Optional computed mood field
timestamp DATETIME              -- When track was added to DB
user_id TEXT FOREIGN KEY        -- Link to users table
```

#### `plays` Table
```sql
id INTEGER PRIMARY KEY AUTOINCREMENT    -- Play record ID
track_id TEXT FOREIGN KEY              -- Link to tracks table
played_at DATETIME                     -- When the song was played (ISO format with TZ)
context TEXT                           -- Spotify context (playlist, album, etc.)
mood_tag INTEGER                       -- Song mood (1-5 scale)
mood_when_listening INTEGER            -- Listener mood (1-5 scale)
tagged_at DATETIME                     -- When mood tags were added
```

#### `download_history` Table
```sql
id INTEGER PRIMARY KEY AUTOINCREMENT    -- Record ID
last_downloaded_at DATETIME            -- Timestamp of last Spotify API call
songs_downloaded INTEGER               -- Count of songs fetched
download_completed_at DATETIME         -- When download process finished
```

### Mood Scale

Both `mood_tag` and `mood_when_listening` use the same 5-point scale:
```
1 = 😢 Very Sad
2 = 😕 Sad  
3 = 😐 Neutral
4 = 😊 Happy
5 = 🤩 Very Happy
```

---

## 🔄 Data Flow

```
1. User launches Streamlit app
   ↓
2. System checks Spotify OAuth token validity
   ↓
3. User clicks "Download New Information"
   ↓
4. System connects to Spotify API via spotipy
   ↓
5. Fetches 50 most recent plays + metadata
   ↓
6. Fetches audio features for each track (batch processing)
   ↓
7. Stores tracks & plays in SQLite database
   ↓
8. Skips duplicates on subsequent downloads (incremental)
   ↓
9. User navigates to Mood Tagging tab
   ↓
10. System shows 10 untagged plays
   ↓
11. User rates each play with:
    a) Song Mood (how does it sound?)
    b) Your Mood (how did you feel?)
   ↓
12. User clicks "Save Both Tags"
   ↓
13. Moods saved with timestamp to plays table
   ↓
14. Progress bar updates
   ↓
15. Ready for ML model training or further analysis
```

---

## ⚠️ Spotify API Limitation

### The Issue
The Spotify Web API endpoint `/v1/me/player/recently-played` returns a **hard maximum of 50 items** with **no way to paginate further back**.

### What We Tested
- ❌ `next_url` pagination (returns empty)
- ❌ `before` parameter with timestamps (returns 0 items)
- ❌ `offset` parameter (ignored by Spotify)
- ❌ Date range queries (returns 0 items)
- ❌ All other pagination approaches

### Current Behavior
- **First Download**: 50 most recent plays
- **Incremental Updates**: New plays since last download (if user has listened to new songs)
- **Historical Data**: NOT AVAILABLE from Spotify

### Impact on ML Training
| Dataset Size | Viability | Notes |
|---|---|---|
| 50 songs | Limited | Good MVP, small but workable |
| 100+ songs | Better | Achievable in 2-4 weeks with usage |
| 300+ songs | Ideal | Not possible via Spotify API |

### Workaround Strategy
- Start with 50 songs
- Run incremental downloads weekly
- Dataset grows naturally with listening
- Use techniques for small ML datasets (regularization, data augmentation)
- Plan for incremental model retraining

---

## 🎮 How to Use the Application

### First Time Setup
1. Click "🔄 Download New Information" in Data Management tab
2. System fetches your 50 most recent plays
3. Wait for "✅ Download complete!" message

### Mood Tagging Workflow
1. Go to "🎵 Mood Tagging" tab
2. For each play, rate:
   - **Left column (Song Mood)**: How does this song sound?
   - **Right column (Your Mood)**: How did YOU feel when listening?
3. Click "💾 Save Both Tags"
4. Repeat until progress bar shows 100%

### Viewing Your Data
1. Go to "📊 Database Viewer" tab
2. Select a table (plays, tracks, users, etc.)
3. Optionally search or export to CSV
4. Use CSV for external analysis or backup

### Incremental Updates
1. Come back later after listening to more songs
2. Click "🔄 Download New Information" again
3. Only NEW plays are added (duplicates skipped)
4. Continue tagging new plays

---

## 🔧 Development & Debugging

### Logging
All modules use Python's logging module with INFO level:
```python
import logging
logger = logging.getLogger(__name__)
logger.info("Message here")
```

Logs appear in terminal when running Streamlit/FastAPI.

### Common Issues

**Issue**: "No valid token found"
- **Solution**: Run `/login` endpoint first, then refresh browser

**Issue**: "Database is locked"
- **Solution**: Close all Streamlit/Python instances, delete `db.sqlite`, restart

**Issue**: Only 50 songs despite clicking download multiple times
- **Solution**: This is expected! Spotify API limitation. New plays appear only when you listen to new songs.

**Issue**: Mood tags not saving
- **Solution**: Check browser console for errors, ensure database is writable

### Token Management
Tokens are auto-refreshed and stored in `tokens.json`:
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "user-read-recently-played user-library-read",
  "expires_at": 1234567890
}
```

Manual refresh is never needed thanks to JavaScript polling in auth flow.

---

## 📈 Data Analytics Ideas

Once you have 50+ songs tagged, you can:

### Mood Distribution
- What % of your songs are very sad vs very happy?
- How does your listening mood differ from song mood?
- Are you using happy songs to lift mood or sad songs to match?

### Audio Features Correlation
- Do happy songs have higher valence/tempo?
- Do sad songs have lower energy/danceability?
- Build feature → mood prediction model

### Time-Based Analysis
- When do you listen to which moods?
- Morning vs evening listening patterns?
- Mood trends over time?

### Playlist Generation
- Create playlists by mood
- Recommend songs based on current mood
- Suggest songs you haven't heard with similar audio features

---

## 🚧 Future Development

### Phase 2: ML Model Training
- Build mood prediction model (audio features → mood)
- Test accuracy on tagged data
- Handle small dataset challenges

### Phase 3: Recommendations
- Recommend untagged songs by predicted mood
- Smart playlist generation
- Mood-based shuffle

### Phase 4: Advanced Features
- Time-of-day mood patterns
- Mood journey visualization
- Collaborative playlists
- Mobile app (React Native/Flutter)

### Phase 5: Scale-Up
- Accumulate 300+ songs over time
- Retrain model incrementally
- User feedback loop
- Public API for external apps

---

## 📝 File Manifest

### Essential Production Files (Keep)
- `app.py` - Core backend
- `auth_helpers.py` - OAuth management
- `token_manager.py` - Token persistence
- `db_utils.py` - Database operations
- `ingest.py` - Data collection
- `spotify_ops.py` - Playlist operations
- `streamlit_tag.py` - Main UI
- `streamlit_ui.py` - Legacy dashboard (optional but included)
- `requirements.txt` - Dependencies
- `.env.example` - Config template
- `PROJECT_DOCUMENTATION.md` - This file
- `README.md` - Quick reference

### Test/Debug Files (Removed)
- ❌ `test_ingest.py` - Testing script
- ❌ `test_api_raw.py` - Raw API testing
- ❌ `test_cursor.py` - Cursor testing
- ❌ `test_next_url.py` - Pagination testing
- ❌ `test_limits.py` - API limits testing
- ❌ `test_date_range.py` - Date range testing
- ❌ `create_test_playlist.py` - Test playlist creation
- ❌ `init_db.py` - One-time initialization script

### Old Documentation (Removed/Consolidated)
- ❌ `CURRENT_STATUS.md` - Merged into this file
- ❌ `API_LIMITATION_RESOLUTION.md` - Merged into this file
- ❌ `SPOTIFY_API_LIMITATION.md` - Merged into this file
- ❌ `AUTH_IMPROVEMENTS.md` - Merged into this file
- ❌ `LOGIN_FLOW_IMPROVEMENTS.txt` - Merged into this file
- ❌ `LOGIN_FLOW_SUMMARY.md` - Merged into this file
- ❌ `IMPROVEMENTS.md` - Merged into this file
- ❌ `APP_NAVIGATION_GUIDE.md` - Merged into this file
- ❌ `TAGGING_APP_GUIDE.md` - Merged into this file

---

## 🎓 Progress Timeline

### Session 1: Code Analysis & Critical Fixes
- Analyzed entire codebase (11 files)
- Fixed 14 critical issues
- Standardized naming conventions
- Added error handling

### Session 2: OAuth Flow Redesign
- Removed manual refresh token requirement
- Implemented automatic token refresh
- Added JavaScript polling for auth callback
- Created /me/profile and /logout endpoints

### Session 3: Database Unification
- Unified schema across all modules
- Added missing columns (duration_ms, popularity)
- Implemented mood_when_listening field
- Added download_history tracking

### Session 4: UI Feature Expansion
- Created streamlit_tag.py with three-tab interface
- Implemented mood tagging with progress tracking
- Added database viewer with search/export
- Added data management downloads

### Session 5: Pagination Debugging
- Discovered Spotify API hard 50-item limit
- Tested 5 different pagination approaches
- Documented limitation thoroughly
- Updated code to work within constraints

### Session 6: Two-Mood System Implementation (Today)
- Added separate Song Mood and Your Mood fields
- Updated UI with side-by-side selectors
- Updated statistics to require both moods tagged
- Consolidated all documentation

---

## ✅ Checklist: Ready for Production

- [x] Authentication working (OAuth2 with auto-refresh)
- [x] Data collection functional (50 songs from Spotify)
- [x] Database schema unified and tested
- [x] Mood tagging interface complete
- [x] Database viewer with export
- [x] Incremental update logic
- [x] Error handling throughout
- [x] Comprehensive logging
- [x] Documentation complete
- [x] All test files cleaned up
- [x] Code ready for team handoff

---

## 📞 Support & References

### Spotify API Documentation
- https://developer.spotify.com/documentation/web-api
- https://developer.spotify.com/documentation/web-api/reference/#/operations/get-recently-played
- https://spotipy.readthedocs.io

### FastAPI Documentation
- https://fastapi.tiangolo.com

### Streamlit Documentation
- https://docs.streamlit.io

### SQLite Documentation
- https://www.sqlite.org/docs.html

---

## 📄 Document Information

**Version**: 1.0  
**Last Updated**: November 15, 2025  
**Status**: Complete MVP - Ready for Development Phase 2  
**Maintainer**: Development Team

---

*This document consolidates all project information, progress reports, and technical specifications into a single comprehensive reference. For quick start, see README.md. For production deployment, refer to the File Manifest section.*
