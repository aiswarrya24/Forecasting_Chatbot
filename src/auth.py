
# src/auth.py
import os
# Ensure get_tenant_gname is imported as it's used in handlers to set gname
from .db import tenant_exists, get_tenant_gname
from .config import ERROR_CREATOR_AUTH_FAILED

def authenticate_tenant(tname: str) -> bool:
    """
    Authenticates a tenant by checking if the tenant ID exists in the sales data.
    """
    return tenant_exists(tname)

def authenticate_creator(password: str) -> bool:
    """
    Authenticates the creator using a predefined password from environment variables.
    """
    creator_password = os.getenv("CREATOR_PASSWORD")
    return password == creator_password




