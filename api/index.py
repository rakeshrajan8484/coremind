from dotenv import load_dotenv
load_dotenv()

from coremind.server.api import app
print("REGISTERED ROUTES:")
for route in app.routes:
    print(route.path, route.methods)