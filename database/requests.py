from database.models import async_session, User, Anime, Episode, Channel, Setting
from sqlalchemy import select, update, delete, func
from utils.cache import settings_cache


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  USERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def add_user(tg_id: int, full_name: str, username: str) -> None:
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if not user:
            session.add(User(tg_id=tg_id, full_name=full_name, username=username))
            await session.commit()


async def delete_user(tg_id: int) -> None:
    async with async_session() as session:
        await session.execute(delete(User).where(User.tg_id == tg_id))
        await session.commit()


async def get_users_count() -> int:
    async with async_session() as session:
        return await session.scalar(select(func.count(User.id)))


async def get_all_user_ids() -> list[int]:
    """Barcha foydalanuvchilar tg_id larini list sifatida qaytaradi."""
    async with async_session() as session:
        result = await session.scalars(select(User.tg_id))
        return list(result)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CHANNELS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def add_channel(channel_id: int, title: str, invite_link: str) -> None:
    async with async_session() as session:
        session.add(Channel(channel_id=channel_id, title=title, invite_link=invite_link))
        await session.commit()


async def get_channels():
    async with async_session() as session:
        return await session.scalars(select(Channel))


async def delete_channel(channel_id: int) -> None:
    async with async_session() as session:
        await session.execute(delete(Channel).where(Channel.channel_id == channel_id))
        await session.commit()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ANIME
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def get_anime_by_code(code: str):
    async with async_session() as session:
        return await session.scalar(select(Anime).where(Anime.code == code))


async def get_animes_count() -> int:
    async with async_session() as session:
        return await session.scalar(select(func.count(Anime.id)))


async def add_anime(name: str, description: str, image_id: str, code: str):
    async with async_session() as session:
        anime = Anime(name=name, description=description, image_id=image_id, code=code)
        session.add(anime)
        await session.commit()
        return anime


async def check_code(code: str):
    async with async_session() as session:
        return await session.scalar(select(Anime).where(Anime.code == str(code)))


async def get_next_code() -> int:
    async with async_session() as session:
        codes = await session.scalars(select(Anime.code))
        numeric = [int(c) for c in codes if c and str(c).isdigit()]
        return (max(numeric) if numeric else 0) + 1


async def update_anime(anime_id: int, **kwargs) -> None:
    async with async_session() as session:
        await session.execute(update(Anime).where(Anime.id == anime_id).values(**kwargs))
        await session.commit()


async def delete_anime(anime_id: int) -> None:
    async with async_session() as session:
        await session.execute(delete(Anime).where(Anime.id == anime_id))
        await session.commit()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  EPISODES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def get_episodes(anime_id: int):
    async with async_session() as session:
        return await session.scalars(
            select(Episode).where(Episode.anime_id == anime_id).order_by(Episode.part)
        )


async def get_episode_with_anime(ep_id: int, anime_id: int):
    """Bitta so'rovda epizod va animeni oladi."""
    async with async_session() as session:
        episode = await session.scalar(select(Episode).where(Episode.id == ep_id))
        anime = await session.scalar(select(Anime).where(Anime.id == anime_id))
        return episode, anime


async def add_episode(anime_id: int, part: int, file_id: str) -> bool:
    async with async_session() as session:
        exists = await session.scalar(
            select(Episode).where(Episode.anime_id == anime_id, Episode.file_id == file_id)
        )
        if exists:
            return False
        session.add(Episode(anime_id=anime_id, part=part, file_id=file_id))
        await session.commit()
        return True


async def get_last_episode_number(anime_id: int) -> int:
    async with async_session() as session:
        result = await session.scalar(
            select(func.max(Episode.part)).where(Episode.anime_id == anime_id)
        )
        return result or 0


async def update_episode(ep_id: int, **kwargs) -> None:
    async with async_session() as session:
        await session.execute(update(Episode).where(Episode.id == ep_id).values(**kwargs))
        await session.commit()


async def delete_episode(ep_id: int) -> None:
    async with async_session() as session:
        await session.execute(delete(Episode).where(Episode.id == ep_id))
        await session.commit()


async def delete_all_episodes(anime_id: int) -> None:
    async with async_session() as session:
        await session.execute(delete(Episode).where(Episode.anime_id == anime_id))
        await session.commit()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SETTINGS  (baza + kesh sinxron)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def get_setting(key: str, default: str = "") -> str:
    """Avval keshdan, keshda bo'lmasa bazadan oladi."""
    cached = settings_cache.get(key)
    if cached:
        return cached

    async with async_session() as session:
        row = await session.scalar(select(Setting).where(Setting.key == key))
        if row:
            settings_cache.set(key, row.value)
            return row.value
    return default


async def set_setting(key: str, value: str) -> None:
    """Bazaga yozadi VA keshni yangilaydi — bir joyda."""
    async with async_session() as session:
        row = await session.scalar(select(Setting).where(Setting.key == key))
        if row:
            row.value = value
        else:
            session.add(Setting(key=key, value=value))
        await session.commit()

    settings_cache.set(key, value)


async def init_settings_cache() -> None:
    """Bot ishga tushganda barcha sozlamalarni keshga yuklaydi."""
    async with async_session() as session:
        rows = await session.scalars(select(Setting))
        settings_cache.load({row.key: row.value for row in rows})
