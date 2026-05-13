"""Storage protocol and SQLite adapter."""

from leverage_platform.storage.protocol import Store
from leverage_platform.storage.sqlite import SQLiteStore

__all__ = ["SQLiteStore", "Store"]
