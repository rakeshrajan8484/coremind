import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
try:
    conn_str = os.getenv("SUPABASE_CONNECTION_STRING")
    print(f"Connecting to: {conn_str.split('@')[1] if '@' in conn_str else '??'}")
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()
    cur.execute("SELECT 1;")
    print("Success DB Connection:", cur.fetchone())
    conn.close()
except Exception as e:
    print(f"Failed: {e}")
