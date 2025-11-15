# 🚀 Quick Start - Testing the Improved Login Flow

## What Changed?

**Before:** Click login → see success in Spotify window → come back → click login again → finally see dashboard

**Now:** Click login → automatic detection → dashboard loads instantly ✨

## Getting Started (5 minutes)

### Step 1: Clean Setup
```bash
# Optional: Remove old token (if you want fresh start)
rm tokens.json

# Ensure you're in the project directory
cd "Spotiffy IA"
```

### Step 2: Start Services

**Terminal 1 - API Server:**
```bash
uvicorn app:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

**Terminal 2 - Streamlit Dashboard:**
```bash
streamlit run streamlit_ui.py
```

You should see:
```
You can now view your Streamlit app in your browser.
Local URL: http://localhost:8501
```

### Step 3: Test the Login Flow

1. **Open Streamlit** at `http://localhost:8501`
2. You should see the welcome screen in the center
3. In the **left sidebar**, click the blue **"🔗 Login with Spotify"** button
4. A **new window will open** with Spotify login (width=500, height=700)
5. **Sign in with your Spotify account** (or create free account at spotify.com)
6. **Click "Agree"** on the permissions screen
7. Watch the Streamlit page (don't close the original window!)
8. Within 2-4 seconds, the page should **automatically refresh**
9. You should see:
   - ✅ Your profile picture (if you have one)
   - ✅ Your Spotify display name
   - ✅ Your email address
   - ✅ Three tabs: "🔥 Top Tracks", "🎧 Recently Played", "🎼 Playlists"

### Step 4: Explore Features

**View Top Tracks:**
- Click the "🔥 Top Tracks" tab
- Move the slider to select how many tracks (1-50)
- Click "📥 Load Top Tracks"
- Your top tracks will appear with artist names and popularity scores

**View Recently Played:**
- Click the "🎧 Recently Played" tab
- Move the slider to select track count
- Click "📥 Load Recently Played"
- See your recent listening history with timestamps

**Logout:**
- Scroll down in the sidebar
- Click the red "🚪 Logout" button
- Page refreshes and shows login screen again

## Troubleshooting

### Problem: Auth window doesn't open
**Solution:**
- Check if popup is blocked by browser
- Allow popups for localhost:8501
- Try a different browser

### Problem: Page doesn't refresh after auth
**Solution:**
- Keep the Streamlit tab open and active
- Wait up to 60 seconds (polling runs for max 60 sec)
- Check browser console for JavaScript errors (F12)
- Make sure API server (uvicorn) is running

### Problem: "API Server: Unreachable"
**Solution:**
- Verify uvicorn is running: `netstat -ano | grep 8000`
- Restart uvicorn: `uvicorn app:app --reload`
- Check `.env` has `FASTAPI_URL=http://127.0.0.1:8000`

### Problem: Can't see profile info after login
**Solution:**
- Refresh the page manually (Ctrl+R)
- Delete `tokens.json` and try again
- Check that Spotify credentials in `.env` are correct

## What's Happening Behind the Scenes

1. **JavaScript Polling** (in browser)
   - After you click login, JavaScript checks every 2 seconds
   - It tests the `/me/profile` API endpoint
   - Once it gets a successful response, it tells Streamlit to refresh

2. **Token Management** (on your computer)
   - Spotify auth redirects to `/callback` endpoint
   - `/callback` saves your access token to `tokens.json`
   - Token lasts ~1 hour and auto-refreshes when needed

3. **Auto-Detection** (in Streamlit)
   - After page refresh, checks if valid token exists
   - If yes, loads your profile picture and name
   - Shows dashboard with all features

## Expected Output

### Successful Login Sequence
```
[Browser Console]
Authorization URL generated
[Spotify window opens]
[User authorizes]
[JavaScript polling: attempt 1... 2... 3...]
[After ~6 seconds]
[Streamlit page refreshes automatically]
[Profile loads with avatar]
[Dashboard displays]
```

### In Terminal (API Server)
```
INFO:     POST /callback HTTP/1.1" 200
INFO:     User authenticated successfully
INFO:     GET /me/profile HTTP/1.1" 200
```

### In Terminal (Streamlit)
```
2025-11-15 12:34:56 - INFO - User authenticated: John Doe
2025-11-15 12:34:57 - INFO - Profile fetched: john.spotify.id
```

## Next Steps

Once login is working:

1. **Explore Endpoints:**
   ```bash
   # Test API directly
   curl http://localhost:8000/health
   curl http://localhost:8000/me/profile
   curl "http://localhost:8000/me/top-tracks?limit=5"
   ```

2. **Check Database:**
   ```bash
   # View created database
   sqlite3 db.sqlite ".tables"  # See: users, tracks
   ```

3. **Ingest Music Data:**
   ```bash
   python ingest.py  # Load your listening history
   ```

## Key Features

✅ **Single Click Auth** - No refresh needed
✅ **Auto-Detection** - Knows when you're logged in
✅ **User Profile** - Shows avatar and info
✅ **One-Click Logout** - Clean session clearing
✅ **Error Handling** - Clear error messages
✅ **Timeout Protection** - Won't hang forever
✅ **Responsive UI** - Works on mobile too

## Architecture Diagram

```
┌─────────────────┐
│   You           │
│ (Web Browser)   │
└────────┬────────┘
         │
    1. Click Login
         │
    ┌────┴──────────────────┬─────────────┐
    │                        │             │
    ▼                        ▼             ▼
┌─────────────┐    ┌──────────────────┐  ┌─────────────┐
│ Streamlit   │    │ Spotify Auth     │  │ API Server  │
│ (Port 8501) │    │ (Popup Window)   │  │ (Port 8000) │
└─────────────┘    └──────────────────┘  └─────────────┘
    │                      │                    │
    │ 3. Wait for token    │ 2. User clicks OK │
    │ (polling every 2s)   │                   │
    │◄────JavaScript───────┤                   │
    │                      │                   │
    │                      │ 4. Auth success   │
    │                      │                   │
    │◄─────────/callback──────────────────────┤
    │                      │                   │
    │ 5. Poll success!     │                   │
    │ Page auto-refresh    │                   │
    │                      │                   │
    │ 6. Get profile       │                   │
    └─────────────/me/profile─────────────────►
                           │
                    7. Return user info
```

## Common Questions

**Q: Is my data safe?**
A: Yes! Your token is stored locally on your computer. Only you can access it.

**Q: What if I don't authorize?**
A: The page will wait for 60 seconds, then timeout. Just click the button again.

**Q: Can I use this on my phone?**
A: Not yet, but the UI is designed to be mobile-friendly for future versions.

**Q: How long do tokens last?**
A: Access tokens last 1 hour. They auto-refresh automatically.

**Q: What happens if I close the Spotify window?**
A: The page will timeout after 60 seconds and return to login screen. Just click login again.

**Q: Can multiple people use this?**
A: Yes! Each person needs their own Spotify account. Tokens are per-device.

---

**Ready to test?** Start the servers and click "Login with Spotify" in the sidebar! 🎵
