"""
Oddiy in-memory kesh.
Faqat sozlamalar (ad_text, channel_username) saqlanadi — 
2-3 ta kalit, xotira yuklamasi ~0.
"""


class SettingsCache:
    __slots__ = ("_store",)

    def __init__(self):
        self._store: dict[str, str] = {}

    # ── O'qish ──────────────────────────────────────────
    def get(self, key: str, default: str = "") -> str:
        return self._store.get(key, default)

    # ── Yozish (bitta kalit) ────────────────────────────
    def set(self, key: str, value: str) -> None:
        self._store[key] = value

    # ── Bulk yuklash (bot ishga tushganda) ──────────────
    def load(self, pairs: dict[str, str]) -> None:
        self._store.update(pairs)

    # ── Debug uchun ─────────────────────────────────────
    def __repr__(self) -> str:
        return f"SettingsCache({self._store})"


# Global singleton — barcha modullar shu obyektni ishlatadi
settings_cache = SettingsCache()
