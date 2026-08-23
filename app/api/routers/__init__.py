"""HTTP routers. Each is a thin layer over `app.domain`."""

from app.api.routers import auth, board, buckets, completions, habits, settings

__all__ = ["auth", "board", "buckets", "completions", "habits", "settings"]
