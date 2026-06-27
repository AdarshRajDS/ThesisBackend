from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
import os

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

print("URL:", url)
print("KEY length:", len(key) if key else None)

supabase = create_client(url, key)

try:
    buckets = supabase.storage.list_buckets()
    print("✅ AUTH SUCCESS")
except Exception as e:
    print("❌ AUTH FAILED:", e)