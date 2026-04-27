from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, StateFilter
import database.requests as rq
from utils.cache import settings_cache

router = Router()


def _build_caption(anime_name: str, part: int) -> str:
    """Dinamik caption: anime nomi + qism + keshdan reklama."""
    caption = f"🎬 {anime_name}\n🎞 {part}-qism"

    username = settings_cache.get("channel_username")
    ad_text = settings_cache.get("ad_text")

    footer_parts = [p for p in (username, ad_text) if p]
    if footer_parts:
        caption += "\n\n" + "\n".join(footer_parts)

    return caption


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        f"Salom {message.from_user.full_name}!\n\nAnime qidirish uchun anime kodini yuboring."
    )


@router.message(F.text.isdigit(), StateFilter(None))
async def search_anime(message: Message):
    anime = await rq.get_anime_by_code(message.text)
    if not anime:
        return await message.answer("❌ Bunday kodli anime topilmadi.")

    episodes = await rq.get_episodes(anime.id)
    episodes_list = list(episodes)

    if not episodes_list:
        return await message.answer(f"🎬 **{anime.name}**\n\nBu anime uchun hali qismlar yuklanmagan.")

    text = (
        f"🎬 **{anime.name}**\n\n{anime.description}\n\n"
        f"Qismlar soni: {len(episodes_list)}\n\nKo'rmoqchi bo'lgan qismini tanlang:"
    )

    buttons = []
    row = []
    for ep in episodes_list:
        row.append(InlineKeyboardButton(text=str(ep.part), callback_data=f"ep_{anime.id}_{ep.id}"))
        if len(row) == 5:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    if anime.image_id:
        await message.answer_photo(photo=anime.image_id, caption=text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("ep_"))
async def send_episode(callback: CallbackQuery):
    _, anime_id, ep_id = callback.data.split("_")

    episode, anime = await rq.get_episode_with_anime(int(ep_id), int(anime_id))

    if not episode:
        return await callback.answer("❌ Epizod topilmadi.", show_alert=True)

    caption = _build_caption(anime.name, episode.part)

    await callback.message.answer_video(video=episode.file_id, caption=caption)
    await callback.answer()


@router.callback_query(F.data == "check_sub")
async def check_subscription(callback: CallbackQuery):
    await callback.answer("Tekshirilmoqda...")
    await callback.message.delete()
    await callback.message.answer("Tabriklaymiz! Endi botdan foydalanishingiz mumkin. Qidiruv kodini yuboring.")
