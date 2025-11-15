# Spotify AI - Mood-Based Playlist Generator

A Python application that analyzes your Spotify listening history and tags songs with moods to build a mood-based playlist recommendation system.

## ⚡ Quick Start

### 1. Setup (5 minutes)

```bash
# Clone/navigate to project
cd "c:\Users\matiz\OneDrive\Escritorio\Spotiffy IA"

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Spotify OAuth

1. Create a free app at https://developer.spotify.com
2. Copy `.env.example` to `.env`
3. Add your credentials:
   ```
   SPOTIFY_CLIENT_ID=your_id
   SPOTIFY_CLIENT_SECRET=your_secret
   REDIRECT_URI=http://localhost:8000/auth/callback
   ```

### 3. Run the Application

**Terminal 1 - Backend**:
```bash
uvicorn app:app --reload --port 8000
```

**Terminal 2 - Frontend**:
```bash
streamlit run streamlit_tag.py
```

### 4. Start Using

1. Click "Login with Spotify" → Authorize
2. Go to "Data Management" tab → Click "Download New Information"
3. Wait for your 50 songs to download
4. Go to "Mood Tagging" tab → Start tagging!

**Tag both**:
- **Song Mood**: How does the song sound?
- **Your Mood**: How did YOU feel when listening?

---

## 📚 Full Documentation

For comprehensive information including:
- Complete feature list
- Database schema
- Technical architecture
- Data analytics ideas
- Future development roadmap
- Troubleshooting guide

👉 See **PROJECT_DOCUMENTATION.md**

---

## ⚠️ Important Note

**Spotify API Limitation**: The system downloads a maximum of **50 recent plays** from Spotify. This is a documented API limitation with no workaround. The dataset grows over time as you listen to new songs and run incremental updates.

---

## 📂 Project Files

**Core Application**:
- `app.py` - FastAPI backend
- `streamlit_tag.py` - Main mood tagging UI
- `ingest.py` - Download Spotify data
- `db_utils.py` - Database operations

**Configuration**:
- `.env` - Spotify credentials (create from .env.example)
- `requirements.txt` - Python dependencies

**Documentation**:
- `PROJECT_DOCUMENTATION.md` - Complete reference (START HERE)
- `QUICK_START.md` - Alternative setup guide

---

## 🎯 Features

✅ Secure Spotify OAuth login  
✅ Download 50 most recent plays  
✅ Two-mood tagging system (song mood + your mood)  
✅ Database viewer with search/export  
✅ Incremental updates (new plays only)  
✅ Full datetime tracking  
✅ Progress tracking  
✅ CSV export for analysis  

---

## 🚀 Next Steps

1. **Tag 20-30 songs** with both moods
2. **Export data** via Database Viewer
3. **Analyze patterns** in your mood tags
4. **Plan Phase 2**: Build ML mood predictor

---

## 📞 Need Help?

See **PROJECT_DOCUMENTATION.md** for:
- Troubleshooting guide
- Data analytics ideas
- Database schema details
- Development instructions

---

**Status**: ✅ MVP Complete  
**Last Updated**: November 15, 2025
