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

# Optional service role (admin) client - create lazily so env changes take effect without restart
supabase_admin: Client | None = None

def get_supabase() -> Client:
    return supabase


def get_supabase_admin() -> Client | None:
    """Return an admin Supabase client if SUPABASE_SERVICE_ROLE_KEY is set.

    This function reloads environment variables from .env (if present) and will
    create the admin client lazily. This allows adding SUPABASE_SERVICE_ROLE_KEY
    to .env without restarting the process (you still need to ensure .env is
    updated in the working directory or env var exported to the process).
    """
    global supabase_admin
    # Ensure .env changes are loaded if the developer edited the .env file
    try:
        from dotenv import load_dotenv
        load_dotenv(override=False)
    except Exception:
        pass

    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    if not key:
        return None

    if supabase_admin:
        return supabase_admin

    try:
        new_admin = create_client(SUPABASE_URL, key)
        supabase_admin = new_admin
        try:
            import logging
            logging.getLogger(__name__).info("Supabase admin client created from SUPABASE_SERVICE_ROLE_KEY")
        except Exception:
            pass
        return supabase_admin
    except Exception as e:
        try:
            import logging
            logging.getLogger(__name__).error(f"Failed to create Supabase admin client: {e}")
        except Exception:
            pass
        return None
