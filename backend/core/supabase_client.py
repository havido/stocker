"""
Supabase client singleton.

Provides two clients:
- `get_supabase()` → anon-key client (for auth operations)
- `get_supabase_admin()` → service-role client (for database operations)
"""

import os
from functools import lru_cache
from supabase import create_client, Client


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """Public (anon-key) client — used for auth sign-up / sign-in."""
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)


@lru_cache(maxsize=1)
def get_supabase_admin() -> Client:
    """Service-role client — bypasses RLS for server-side DB operations."""
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)
