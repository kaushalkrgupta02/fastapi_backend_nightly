from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

missing = [name for name, val in (("SUPABASE_URL", SUPABASE_URL), ("SUPABASE_ANON_KEY", SUPABASE_ANON_KEY)) if val is None]
if missing:
    raise RuntimeError(f"Missing environment variables: {', '.join(missing)}; please set them in your environment or .env file")

# help the type checker narrow Optional[str] -> str
assert SUPABASE_URL is not None and SUPABASE_ANON_KEY is not None

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

def get_supabase() -> Client:
    # print("Returning Supabase client instance")
    return supabase

# get_supabase()