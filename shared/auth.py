"""Lightweight API-key auth for service write endpoints.

If `API_KEY` is unset, auth is disabled (dev mode) and a warning is logged once.
When set, POST requests must include header `X-API-Key: <key>` or query `?api_key=<key>`.
GET requests (UI/dashboards) remain open so the HTML pages still work in a browser.
"""
import os
from functools import wraps
from flask import request, jsonify

from shared.logger import setup_logger

logger = setup_logger("auth")

_API_KEY = os.getenv("API_KEY", "").strip()
_warned = False


def _check_key() -> bool:
    global _warned
    if not _API_KEY:
        if not _warned:
            logger.warning("API_KEY not set — auth disabled (dev mode). Set API_KEY in .env for production.")
            _warned = True
        return True
    provided = request.headers.get("X-API-Key") or request.args.get("api_key")
    return provided == _API_KEY


def require_api_key(fn):
    """Decorator: enforce API key on POST; let GET through (for HTML UI)."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if request.method == "POST" and not _check_key():
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
        return fn(*args, **kwargs)
    return wrapper
