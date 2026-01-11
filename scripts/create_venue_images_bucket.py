"""Create "venue-images" bucket in Supabase storage using a service role key.

Usage:
  Set environment variables SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY then run:
    python scripts/create_venue_images_bucket.py

This script attempts several create_bucket signatures to work across supabase client versions.
"""
import os
import sys
import logging

try:
    from supabase import create_client
except Exception as e:
    print("supabase-py is required: pip install supabase-client or supabase-py", file=sys.stderr)
    raise

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SERVICE_KEY:
    logger.error("Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in your environment before running this script.")
    sys.exit(1)

client = create_client(SUPABASE_URL, SERVICE_KEY)
BUCKET_NAME = os.getenv('SUPABASE_BUCKET_NAME', 'venue-images')  # override with SUPABASE_BUCKET_NAME env var if set

def try_create_bucket():
    # Try a few signatures to be robust against client versions
    attempts = []
    try:
        logger.info(f"Attempting create_bucket('{BUCKET_NAME}')")
        attempts.append(('no_args', client.storage.create_bucket(BUCKET_NAME)))
        return attempts[-1][1]
    except TypeError as te:
        logger.debug(f"TypeError with no_args: {te}")
    except Exception as e:
        logger.debug(f"Error with no_args: {e}")

    try:
        logger.info(f"Attempting create_bucket('{BUCKET_NAME}', {{'public': True}})")
        attempts.append(('options_dict', client.storage.create_bucket(BUCKET_NAME, {'public': True})))
        return attempts[-1][1]
    except TypeError as te:
        logger.debug(f"TypeError with options_dict: {te}")
    except Exception as e:
        logger.debug(f"Error with options_dict: {e}")

    try:
        logger.info(f"Attempting create_bucket('{BUCKET_NAME}', is_public=True)")
        attempts.append(('is_public_kw', client.storage.create_bucket(BUCKET_NAME, is_public=True)))
        return attempts[-1][1]
    except Exception as e:
        logger.debug(f"Error with is_public_kw: {e}")
        raise

if __name__ == '__main__':
    try:
        resp = try_create_bucket()
        logger.info(f"Create bucket response: {resp}")
        # Some clients return dicts with error key
        if isinstance(resp, dict) and resp.get('error'):
            logger.error(f"Create bucket failed: {resp}")
            sys.exit(2)
        logger.info(f"Bucket '{BUCKET_NAME}' created or already exists.")
    except Exception as e:
        logger.exception("Bucket creation failed")
        sys.exit(1)
