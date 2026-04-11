from dotenv import load_dotenv
load_dotenv()

from coremind.server.api import app
from coremind.storage.session_store import SessionStore
print("REGISTERED ROUTES:")
for route in app.routes:
    print(route.path, route.methods)

SESSION_STORE = SessionStore()

@app.on_event("startup")
async def startup():
    await SESSION_STORE.initialize()