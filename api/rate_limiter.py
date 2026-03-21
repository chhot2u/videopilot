"""API rate limiting utilities."""

from fastapi import HTTPException, Request
from starlette.status import HTTP_429_TOO_MANY_REQUESTS
from datetime import datetime, timedelta
from typing import Dict, Optional

# Rate limits configuration (requests per minute)
RATE_LIMITS = {
    "default": 60,  # 60 requests per minute for unauthenticated users
    "authenticated": 300,  # 300 requests per minute for authenticated users
}

# Store for tracking API calls
api_call_store: Dict[str, Dict[str, any]] = {}


def get_client_identifier(request: Request) -> str:
    """Get a unique identifier for the client."""
    # Check for API key in headers
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return api_key
    
    # Fallback to client IP address
    client_ip = request.client.host if request.client else "unknown"
    return client_ip


def is_rate_limit_exceeded(client_id: str, is_authenticated: bool = False) -> bool:
    """Check if the client has exceeded their rate limit."""
    now = datetime.now()
    limit = RATE_LIMITS["authenticated"] if is_authenticated else RATE_LIMITS["default"]
    window = timedelta(minutes=1)
    
    if client_id not in api_call_store:
        api_call_store[client_id] = {"calls": [], "window_start": now}
    
    client_data = api_call_store[client_id]
    
    # Clean up old calls outside the current window
    client_data["calls"] = [
        call_time for call_time in client_data["calls"]
        if call_time > now - window
    ]
    
    # Check if rate limit is exceeded
    if len(client_data["calls"]) >= limit:
        return True
    
    # Record the new call
    client_data["calls"].append(now)
    return False


def rate_limit_checker(request: Request, api_key: str = None) -> None:
    """Rate limit checker dependency."""
    client_id = get_client_identifier(request)
    is_authenticated = bool(api_key)
    
    if is_rate_limit_exceeded(client_id, is_authenticated):
        raise HTTPException(
            status_code=HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )
