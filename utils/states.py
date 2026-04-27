from aiogram.fsm.state import StatesGroup, State


# ── Tarqatish (Broadcast) ───────────────────────────────
class BroadcastState(StatesGroup):
    type = State()        # copy / forward (eski)
    message = State()     # eski broadcast xabari
    media_post = State()  # 📮 rasm/video + caption
    text_post = State()   # 📩 faqat matn


# ── Kanal Post ─────────────────────────────────────────
class ChannelPostState(StatesGroup):
    channel    = State()   # kanal tanlash
    anime_code = State()   # anime kodi kiritish
    method     = State()   # asliday / qolda
    content    = State()   # qo'lda: admin media yoki matn yuboradi


# ── Sozlamalar ──────────────────────────────────────────
class SettingsState(StatesGroup):
    ad_text = State()
    channel_username = State()


# ── Anime CRUD ──────────────────────────────────────────
class AnimeState(StatesGroup):
    name = State()
    status = State()
    parts = State()
    genres = State()
    code = State()
    image = State()


# ── Epizod qo'shish ────────────────────────────────────
class EpisodeState(StatesGroup):
    anime_code = State()
    part = State()
    video = State()


# ── Kanal boshqarish ───────────────────────────────────
class ChannelState(StatesGroup):
    channel_id = State()
    title = State()
    link = State()


# ── O'chirish ──────────────────────────────────────────
class DeleteState(StatesGroup):
    code = State()


class DeleteAnimeFullState(StatesGroup):
    code = State()
    confirm = State()


# ── Tahrirlash ─────────────────────────────────────────
class EditAnimeState(StatesGroup):
    code = State()
    choice = State()
    new_value = State()


class EditEpisodeState(StatesGroup):
    anime_code = State()
    choice = State()
    new_video = State()
