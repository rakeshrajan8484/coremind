from dotenv import load_dotenv
load_dotenv()

from coremind.server.api import app
from coremind.storage.session_store import SessionStore

# -----------------------------
# Debug routes (optional)
# -----------------------------
print("REGISTERED ROUTES:")
for route in app.routes:
    print(route.path, route.methods)

# -----------------------------
# Global Session Store
# -----------------------------
SESSION_STORE = SessionStore()


# -----------------------------
# Lazy init (Vercel-safe)
# -----------------------------
async def get_session_store():
    if SESSION_STORE.pool is None:
        await SESSION_STORE.initialize()
    return SESSION_STORE


# -----------------------------
# Attach to app state (optional but clean)
# -----------------------------
app.state.session_store = SESSION_STORE
app.state.get_session_store = get_session_store