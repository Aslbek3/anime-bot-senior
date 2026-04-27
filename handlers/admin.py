import asyncio
import logging
import platform
import time
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramForbiddenError

import database.requests as rq
from data.config import ADMINS
from keyboards.reply import admin_main_keyboard, broadcast_type_keyboard, anime_settings_keyboard
from utils.states import BroadcastState, ChannelPostState, ChannelState, AnimeState, EpisodeState, DeleteState, DeleteAnimeFullState, EditAnimeState, EditEpisodeState, SettingsState

router = Router()
# Admin filtrini butun router uchun qo'llaymiz (faqat adminlar bu routerga kiradi)
router.message.filter(F.from_user.id.in_(ADMINS))

episode_lock = asyncio.Lock()

@router.message(CommandStart())
async def admin_cmd_start(message: Message, state: FSMContext):
    await state.clear()
    # Foydalanuvchi bo'limiga o'tkazamiz (start xabarini yuboramiz)
    await message.answer(f"Salom {message.from_user.full_name}!\n\nAnime qidirish uchun anime kodini yuboring.", reply_markup=ReplyKeyboardMarkup(keyboard=[], remove_keyboard=True))

@router.message(Command("admin"))
async def admin_panel(message: Message):
    await message.answer("Xush kelibsiz Admin! Kerakli bo'limni tanlang:", reply_markup=admin_main_keyboard())

@router.message(F.text == "📊 Statistika")
async def admin_stats(message: Message):
    u_count = await rq.get_users_count()
    a_count = await rq.get_animes_count()
    await message.answer(f"📊 **Bot statistikasi:**\n\n👥 Obunachilar: {u_count}\n🎬 Animelar: {a_count}")

@router.message(F.text == "Xabar Yuborish")
async def broadcast_start(message: Message, state: FSMContext):
    await message.answer("Xabar yuborish turini tanlang:", reply_markup=broadcast_type_keyboard())
    await state.set_state(BroadcastState.type)

@router.message(BroadcastState.type, F.text.in_(["📤 Copy (Asliday)", "🔄 Forward (Muallif bilan)"]))
async def broadcast_type_chosen(message: Message, state: FSMContext):
    await state.update_data(broadcast_type=message.text)
    await message.answer("Yubormoqchi bo'lgan xabaringizni yuboring (har qanday turdagi xabar):", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], resize_keyboard=True))
    await state.set_state(BroadcastState.message)

@router.message(F.text == "❌ Bekor qilish")
async def broadcast_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Amal bekor qilindi.", reply_markup=admin_main_keyboard())

@router.message(BroadcastState.message)
async def broadcast_send(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        return await message.answer("Amal bekor qilindi.", reply_markup=admin_main_keyboard())

    data = await state.get_data()
    b_type = data['broadcast_type']
    await _do_broadcast(message, state, use_forward="Forward" in b_type)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  KANAL POST  (📮 Post tayyorlash  |  📩 TEXT POST)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _channels_keyboard(channels, post_type: str) -> InlineKeyboardMarkup:
    """Bazadagi kanallar ro'yxatini inline keyboard sifatida qaytaradi."""
    buttons = [
        [InlineKeyboardButton(
            text=ch.title,
            callback_data=f"chpost_{post_type}_{ch.channel_id}"
        )]
        for ch in channels
    ]
    buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="chpost_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def _start_channel_post(message: Message, state: FSMContext, post_type: str):
    """Post tayyorlash uchun umumiy kirish: kanallar ro'yxatini ko'rsatadi."""
    channels = list(await rq.get_channels())
    if not channels:
        return await message.answer("❌ Hech qanday kanal qo'shilmagan.\n/add_channel orqali qo'shing.")
    label = "📮 Post tayyorlash" if post_type == "media" else "📩 TEXT POST"
    await message.answer(
        f"{label}\n\nQaysi kanalga yubormoqchisiz?",
        reply_markup=_channels_keyboard(channels, post_type)
    )
    await state.set_state(ChannelPostState.channel)


@router.message(F.text == "📮 Post tayyorlash")
async def channel_media_post_start(message: Message, state: FSMContext):
    await _start_channel_post(message, state, post_type="media")


@router.message(F.text == "📩 TEXT POST")
async def channel_text_post_start(message: Message, state: FSMContext):
    await _start_channel_post(message, state, post_type="text")


@router.callback_query(ChannelPostState.channel, F.data.startswith("chpost_"))
async def channel_post_channel_chosen(callback: CallbackQuery, state: FSMContext):
    if callback.data == "chpost_cancel":
        await state.clear()
        await callback.message.edit_text("Bekor qilindi.")
        await callback.message.answer("Admin panel:", reply_markup=admin_main_keyboard())
        return await callback.answer()

    # chpost_{media|text}_{channel_id}
    parts = callback.data.split("_", 2)
    post_type, channel_id = parts[1], int(parts[2])

    await state.update_data(post_type=post_type, channel_id=channel_id)
    await callback.message.edit_text(
        "Anime kodini yuboring:",
    )
    await state.set_state(ChannelPostState.anime_code)
    await callback.answer()


@router.message(ChannelPostState.anime_code)
async def channel_post_anime_code(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        return await message.answer("Bekor qilindi.", reply_markup=admin_main_keyboard())

    anime = await rq.get_anime_by_code(message.text.strip())
    if not anime:
        return await message.answer("❌ Bunday kodli anime topilmadi. Qaytadan urinib ko'ring:")

    await state.update_data(anime_id=anime.id, anime_code=anime.code, anime_name=anime.name)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Asliday (botdagi kabi)", callback_data="chpost_method_auto")],
        [InlineKeyboardButton(text="✏️ Qo'lda (o'zim yuklayman)", callback_data="chpost_method_manual")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="chpost_cancel")],
    ])
    await message.answer(
        f"🎬 Anime: **{anime.name}** (kod: `{anime.code}`)\n\nPost qanday yuborilsin?",
        reply_markup=kb
    )
    await state.set_state(ChannelPostState.method)


@router.callback_query(ChannelPostState.method, F.data.startswith("chpost_"))
async def channel_post_method_chosen(callback: CallbackQuery, state: FSMContext):
    if callback.data == "chpost_cancel":
        await state.clear()
        await callback.message.edit_text("Bekor qilindi.")
        await callback.message.answer("Admin panel:", reply_markup=admin_main_keyboard())
        return await callback.answer()

    method = callback.data.split("_")[2]  # auto | manual
    await state.update_data(method=method)

    if method == "auto":
        # To'g'ridan kanalga yuboring
        await callback.message.edit_text("⏳ Yuborilmoqda...")
        await _send_channel_post(callback.message, state, bot=callback.bot)
    else:
        data = await state.get_data()
        hint = "media (rasm yoki video) + matn" if data["post_type"] == "media" else "matn"
        await callback.message.edit_text(
            f"Endi post uchun {hint} yuboring.\n"
            f"Pastida anime kanalga o'tkazuvchi tugma avtomatik qo'shiladi."
        )
        await state.set_state(ChannelPostState.content)

    await callback.answer()


@router.message(ChannelPostState.content)
async def channel_post_content_received(message: Message, state: FSMContext):
    """Admin o'zi content yuboradi — qo'lda rejim."""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        return await message.answer("Bekor qilindi.", reply_markup=admin_main_keyboard())

    data = await state.get_data()
    if data["post_type"] == "media" and not (message.photo or message.video):
        return await message.answer("⚠️ Rasm yoki video yuboring.")
    if data["post_type"] == "text" and not message.text:
        return await message.answer("⚠️ Matn yuboring.")

    await _send_channel_post(message, state, bot=message.bot, manual_message=message)


async def _send_channel_post(
    reply_target: Message,
    state: FSMContext,
    bot,
    manual_message: Message | None = None
):
    """
    Kanalga post yuboradi.
    manual_message=None  → asliday (bazadan anime ma'lumotlari)
    manual_message=msg   → qo'lda (admin yuborgan content + tugma)
    """
    data = await state.get_data()
    channel_id = data["channel_id"]
    anime_code  = data["anime_code"]
    anime_name  = data["anime_name"]
    anime_id    = data["anime_id"]
    post_type   = data["post_type"]

    bot_info = await bot.get_me()
    deep_link = f"https://t.me/{bot_info.username}?start={anime_code}"

    watch_btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Ko'rish", url=deep_link)]
    ])

    try:
        if manual_message:
            # --- Qo'lda rejim ---
            caption = manual_message.caption or manual_message.text or ""
            if manual_message.photo:
                await bot.send_photo(
                    chat_id=channel_id,
                    photo=manual_message.photo[-1].file_id,
                    caption=caption,
                    reply_markup=watch_btn
                )
            elif manual_message.video:
                await bot.send_video(
                    chat_id=channel_id,
                    video=manual_message.video.file_id,
                    caption=caption,
                    reply_markup=watch_btn
                )
            else:
                await bot.send_message(
                    chat_id=channel_id,
                    text=caption,
                    reply_markup=watch_btn
                )
        else:
            # --- Asliday rejim ---
            anime = await rq.get_anime_by_code(anime_code)
            if post_type == "media" and anime.image_id:
                caption = f"🎬 **{anime.name}**\n\n{anime.description}"
                await bot.send_photo(
                    chat_id=channel_id,
                    photo=anime.image_id,
                    caption=caption,
                    reply_markup=watch_btn
                )
            else:
                text = f"🎬 **{anime.name}**\n\n{anime.description}"
                await bot.send_message(
                    chat_id=channel_id,
                    text=text,
                    reply_markup=watch_btn
                )

        await reply_target.answer("✅ Post kanalga muvaffaqiyatli yuborildi!", reply_markup=admin_main_keyboard())

    except Exception as e:
        logging.error(f"Kanal post xato [{channel_id}]: {e}")
        await reply_target.answer(f"❌ Xato yuz berdi: {e}", reply_markup=admin_main_keyboard())

    await state.clear()

async def _do_broadcast(message: Message, state: FSMContext, use_forward: bool = False):
    """Yagona broadcast funksiyasi — barcha tarqatish turlari shu yerdan o'tadi."""
    users = await rq.get_all_user_ids()
    count, blocked, errors = 0, 0, 0
    status_msg = await message.answer("🚀 Tarqatish boshlandi...")
    start_time = time.time()

    for user_id in users:
        try:
            if use_forward:
                await message.forward(chat_id=user_id)
            else:
                await message.send_copy(chat_id=user_id)
            count += 1
            if count % 50 == 0:
                try:
                    await status_msg.edit_text(f"🚀 Yuborilmoqda... {count}/{len(users)}")
                except Exception:
                    pass
            # FloodControl: sekundiga ~25 xabar
            await asyncio.sleep(0.04)
        except TelegramForbiddenError:
            blocked += 1
            await rq.delete_user(user_id)
        except Exception as e:
            logging.error(f"Broadcast xato [{user_id}]: {e}")
            errors += 1

    duration = round(time.time() - start_time, 1)
    await status_msg.delete()
    await message.answer(
        f"✅ **Tarqatish yakunlandi!**\n\n"
        f"👤 Qabul qildi: {count}\n"
        f"🚫 Bloklaganlar: {blocked}\n"
        f"❌ Xatoliklar: {errors}\n"
        f"⏱ Vaqt: {duration} soniya",
        reply_markup=admin_main_keyboard()
    )
    await state.clear()

# --- SOZLAMALAR ---

@router.message(F.text == "📝 Reklama matni")
async def settings_ad_start(message: Message):
    current_ad = await rq.get_setting("ad_text", "Hali o'rnatilmagan")
    current_username = await rq.get_setting("channel_username", "Hali o'rnatilmagan")
    
    text = (
        f"📝 **Reklama sozlamalari**\n\n"
        f"📢 Kanal: {current_username}\n"
        f"📄 Matn:\n{current_ad}\n\n"
        f"O'zgartirish uchun kerakli bo'limni tanlang:"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Kanal username", callback_data="set_username")],
        [InlineKeyboardButton(text="📄 Reklama matni", callback_data="set_ad_text")]
    ])
    
    await message.answer(text, reply_markup=kb)

@router.callback_query(F.data == "set_username")
async def set_username_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Yangi kanal username kiriting (masalan: @kanal_nomi):", 
                                  reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], resize_keyboard=True))
    await state.set_state(SettingsState.channel_username)
    await callback.answer()

@router.callback_query(F.data == "set_ad_text")
async def set_ad_text_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Yangi reklama matnini yuboring:", 
                                  reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], resize_keyboard=True))
    await state.set_state(SettingsState.ad_text)
    await callback.answer()

@router.message(SettingsState.channel_username)
async def set_username_save(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        return await message.answer("Bekor qilindi.", reply_markup=admin_main_keyboard())
    
    await rq.set_setting("channel_username", message.text)
    await message.answer(f"✅ Kanal username saqlandi: {message.text}", reply_markup=admin_main_keyboard())
    await state.clear()

@router.message(SettingsState.ad_text)
async def set_ad_text_save(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        return await message.answer("Bekor qilindi.", reply_markup=admin_main_keyboard())
    
    await rq.set_setting("ad_text", message.text)
    await message.answer("✅ Reklama matni saqlandi!", reply_markup=admin_main_keyboard())
    await state.clear()

@router.message(F.text == "📢 Kanallar")
async def manage_channels(message: Message):
    channels = await rq.get_channels()
    text = "📢 **Kanallar ro'yxati:**\n\n"
    for ch in channels:
        text += f"🔹 {ch.title} (ID: `{ch.channel_id}`)\n"
    
    text += "\n➕ **Kanal qo'shish:**\n`/add_channel ID Nomi Link`"
    text += "\n\n➖ **Kanalni o'chirish:**\n`/del_channel ID`"
    await message.answer(text)

@router.message(Command("add_channel"))
async def add_channel_cmd(message: Message, command: CommandObject):
    if not command.args:
        return await message.answer("⚠️ Format: `/add_channel ID Nomi Link`")
    
    try:
        args = command.args.split(maxsplit=2)
        ch_id = int(args[0])
        title = args[1]
        link = args[2]
        
        await rq.add_channel(ch_id, title, link)
        await message.answer(f"✅ Kanal qo'shildi: **{title}**")
    except (ValueError, IndexError):
        await message.answer("❌ Xato! Format: `/add_channel -100123456789 KanalNomi https://t.me/...`")

@router.message(Command("del_channel"))
async def del_channel_cmd(message: Message, command: CommandObject):
    if not command.args:
        return await message.answer("⚠️ Format: `/del_channel ID`")
    
    try:
        ch_id = int(command.args)
        await rq.delete_channel(ch_id)
        await message.answer(f"✅ Kanal o'chirildi (ID: {ch_id})")
    except ValueError:
        await message.answer("❌ Xato! ID faqat raqamlardan (va minusdan) iborat bo'lishi kerak.")

@router.message(F.text == "🎬 Animelar sozlash")
async def anime_settings(message: Message):
    await message.answer("🎬 **Animelar sozlash bo'limi.** Kerakli amalni tanlang:", reply_markup=anime_settings_keyboard())

@router.message(F.text == "➕ Anime qo'shish")
async def add_anime_start(message: Message, state: FSMContext):
    await message.answer("Anime nomini yuboring:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], resize_keyboard=True))
    await state.set_state(AnimeState.name)

@router.message(AnimeState.name)
async def add_anime_name(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        return await message.answer("Bekor qilindi.", reply_markup=anime_settings_keyboard())
    await state.update_data(name=message.text)
    await message.answer("Anime holatini yuboring (masalan: Tugallangan):")
    await state.set_state(AnimeState.status)

@router.message(AnimeState.status)
async def add_anime_status(message: Message, state: FSMContext):
    await state.update_data(status=message.text)
    await message.answer("Qismlar sonini yuboring:")
    await state.set_state(AnimeState.parts)

@router.message(AnimeState.parts)
async def add_anime_parts(message: Message, state: FSMContext):
    await state.update_data(parts=message.text)
    await message.answer("Janrlarni yuboring (masalan: Drama, oʻzga dunyo):")
    await state.set_state(AnimeState.genres)

@router.message(AnimeState.genres)
async def add_anime_genres(message: Message, state: FSMContext):
    await state.update_data(genres=message.text)
    next_code = await rq.get_next_code()
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=f"🤖 Avtomatik ({next_code})")],
        [KeyboardButton(text="❌ Bekor qilish")]
    ], resize_keyboard=True)
    await message.answer("Anime uchun qidiruv kodini yuboring yoki avtomatikni tanlang:", reply_markup=kb)
    await state.set_state(AnimeState.code)

@router.message(AnimeState.code)
async def add_anime_code(message: Message, state: FSMContext):
    if "Avtomatik" in message.text:
        code = message.text.split("(")[1].split(")")[0]
    else:
        code = message.text
        # Unikallikni tekshirish
        exists = await rq.check_code(code)
        if exists:
            return await message.answer("❌ Bu kod bazada mavjud! Boshqa kod kiriting:")

    await state.update_data(code=code)
    await message.answer("Anime uchun muqova (rasm) yuboring:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], resize_keyboard=True))
    await state.set_state(AnimeState.image)

@router.message(AnimeState.image, F.photo)
async def add_anime_image(message: Message, state: FSMContext):
    data = await state.get_data()
    
    # Ma'lumotlarni chiroyli formatlash
    description = (
        f"╭────────────────\n"
        f"├‣  Holati: {data['status']}\n"
        f"├‣  Qismlar: {data['parts']}\n"
        f"├‣  Janr: {data['genres']}\n"
        f"╰────────────────"
    )
    
    await rq.add_anime(data['name'], description, message.photo[-1].file_id, data['code'])
    await message.answer(f"✅ **{data['name']}** muvaffaqiyatli qo'shildi!\n\nAnime kodi: `{data['code']}`", reply_markup=anime_settings_keyboard())
    await state.clear()

@router.message(F.text == "🔙 Orqaga")
async def admin_back(message: Message):
    await message.answer("Asosiy admin paneli:", reply_markup=admin_main_keyboard())

@router.message(F.text.in_(["🔍 Foydalanuvchini boshqarish", "📋 Adminlar"]))
async def anime_edit_del(message: Message):
    await message.answer(f"⚙️ **{message.text}** funksiyasi tez orada qo'shiladi.")

@router.message(F.text == "🎞 Qisim qo'shish")
async def add_episode_start(message: Message, state: FSMContext):
    await message.answer("Qaysi animega qism qo'shmoqchisiz? Anime kodini yuboring:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], resize_keyboard=True))
    await state.set_state(EpisodeState.anime_code)

@router.message(EpisodeState.anime_code)
async def add_episode_code(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        return await message.answer("Bekor qilindi.", reply_markup=anime_settings_keyboard())
    
    anime = await rq.get_anime_by_code(message.text)
    if not anime:
        return await message.answer("❌ Bunday kodli anime topilmadi. Qaytadan urinib ko'ring:")
    
    last_part = await rq.get_last_episode_number(anime.id)
    next_part = last_part + 1
    
    await state.update_data(anime_id=anime.id, anime_name=anime.name, next_part=next_part)
    
    await message.answer(
        f"🎬 Anime: **{anime.name}**\n"
        f"📊 Hozirgi qismlar soni: {last_part}\n\n"
        f"📥 Endi anime qismlarini (videolarni) ketma-ket yuboring.\n"
        f"(Raqamlash {next_part}-qismdan boshlanadi)",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="✅ Tugatish")]], resize_keyboard=True)
    )
    await state.set_state(EpisodeState.video)

# Bu handler endi kerak emas, lekin xatolik bo'lmasligi uchun olib tashlaymiz
# yoki EpisodeState.part holatini o'chirib yuboramiz.

@router.message(EpisodeState.video, (F.video | F.document))
async def add_episode_video(message: Message, state: FSMContext):
    async with episode_lock:
        data = await state.get_data()
        anime_id = data['anime_id']
        next_part = data.get('next_part', 1)
        
        # Fayl ID ni aniqlash
        if message.video:
            file_id = message.video.file_id
        elif message.document and (message.document.mime_type or "").startswith('video'):
            file_id = message.document.file_id
        else:
            return await message.answer("⚠️ Iltimos, video fayl yuboring.")
        
        success = await rq.add_episode(anime_id, next_part, file_id)
        
        if success:
            await message.answer(f"✅ {next_part}-qism saqlandi!")
            await state.update_data(next_part=next_part + 1)
        else:
            await message.answer(f"❌ Bu video allaqachon bazada mavjud yoki raqamda xatolik (Part: {next_part}).")

@router.message(EpisodeState.video, F.text == "✅ Tugatish")
async def add_episode_finish(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Qismlar yuklash yakunlandi.", reply_markup=anime_settings_keyboard())

@router.message(EpisodeState.video)
async def add_episode_invalid(message: Message):
    await message.answer("⚠️ Iltimos, video yuboring yoki '✅ Tugatish' tugmasini bosing.")

@router.message(F.text == "🤖 Bot holati")
async def bot_status(message: Message):
    status = f"🤖 **Bot holati:**\n\n✅ Status: Ishlamoqda\n🖥 OS: {platform.system()}\n🕒 Vaqt: {time.strftime('%H:%M:%S')}"
    await message.answer(status)

@router.message(F.text == "🗑 O'chirish")
async def delete_start(message: Message, state: FSMContext):
    await message.answer("O'chirmoqchi bo'lgan anime kodini yuboring:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], resize_keyboard=True))
    await state.set_state(DeleteState.code)

@router.message(DeleteState.code)
async def delete_code(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        return await message.answer("Bekor qilindi.", reply_markup=anime_settings_keyboard())
    
    anime = await rq.get_anime_by_code(message.text)
    if not anime:
        return await message.answer("❌ Bunday kodli anime topilmadi. Qaytadan urinib ko'ring:")
    
    episodes = await rq.get_episodes(anime.id)
    episodes_list = list(episodes)
    
    buttons = []
    row = []
    for ep in episodes_list:
        row.append(InlineKeyboardButton(text=f"❌ {ep.part}-qism", callback_data=f"del_ep_{ep.id}_{anime.id}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    buttons.append([InlineKeyboardButton(text="🗑 BARCHA QISMLARNI O'CHIRISH", callback_data=f"del_all_eps_{anime.id}")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await message.answer(
        f"🎬 Anime: **{anime.name}**\n\nO'chirmoqchi bo'lgan qismini tanlang yoki butun animeni o'chirib tashlang:",
        reply_markup=keyboard
    )
    await state.clear()

@router.callback_query(F.data.startswith("del_ep_"))
async def delete_episode_handler(callback: CallbackQuery):
    _, _, ep_id, anime_id = callback.data.split("_")
    await rq.delete_episode(int(ep_id))
    await callback.answer("Qism o'chirildi!", show_alert=True)
    
    # Ro'yxatni yangilash
    episodes = await rq.get_episodes(int(anime_id))
    episodes_list = list(episodes)
    
    buttons = []
    row = []
    for ep in episodes_list:
        row.append(InlineKeyboardButton(text=f"❌ {ep.part}-qism", callback_data=f"del_ep_{ep.id}_{anime_id}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="🗑 BARCHA QISMLARNI O'CHIRISH", callback_data=f"del_all_eps_{anime_id}")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    try:
        await callback.message.edit_reply_markup(reply_markup=keyboard)
    except:
        pass

@router.callback_query(F.data.startswith("del_all_eps_"))
async def delete_all_episodes_handler(callback: CallbackQuery):
    anime_id = callback.data.split("_")[3]
    await rq.delete_all_episodes(int(anime_id))
    await callback.message.edit_text(f"✅ Ushbu animening barcha qismlari o'chirib tashlandi.", reply_markup=None)
    await callback.message.answer("Asosiy sozlamalarga qaytdik:", reply_markup=anime_settings_keyboard())
    await callback.answer("Barcha qismlar o'chirildi!", show_alert=True)

@router.message(F.text == "🗑 Anime o'chirish")
async def delete_anime_full_start(message: Message, state: FSMContext):
    await message.answer("O'chirib tashlamoqchi bo'lgan anime kodini yuboring:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], resize_keyboard=True))
    await state.set_state(DeleteAnimeFullState.code)

@router.message(DeleteAnimeFullState.code)
async def delete_anime_full_code(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        return await message.answer("Bekor qilindi.", reply_markup=anime_settings_keyboard())
    
    anime = await rq.get_anime_by_code(message.text)
    if not anime:
        return await message.answer("❌ Bunday kodli anime topilmadi. Qaytadan urinib ko'ring:")
    
    await state.update_data(anime_id=anime.id, anime_name=anime.name)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ha", callback_data="confirm_del_anime_yes"),
         InlineKeyboardButton(text="❌ Yo'q", callback_data="confirm_del_anime_no")]
    ])
    
    await message.answer(f"❓ Haqiqatan ham **{anime.name}** animesini va uning barcha qismlarini o'chirib tashlamoqchimisiz?", reply_markup=kb)
    await state.set_state(DeleteAnimeFullState.confirm)

@router.callback_query(DeleteAnimeFullState.confirm, F.data.startswith("confirm_del_anime_"))
async def delete_anime_full_confirm(callback: CallbackQuery, state: FSMContext):
    if "yes" in callback.data:
        data = await state.get_data()
        await rq.delete_anime(data['anime_id'])
        await callback.message.edit_text(f"✅ **{data['anime_name']}** muvaffaqiyatli o'chirildi.")
        await callback.message.answer("Animelar sozlash bo'limi:", reply_markup=anime_settings_keyboard())
    else:
        await callback.message.edit_text("O'chirish bekor qilindi.")
        await callback.message.answer("Animelar sozlash bo'limi:", reply_markup=anime_settings_keyboard())
    
    await state.clear()
    await callback.answer()

@router.message(F.text == "📝 Tahrirlash")
async def edit_start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Anime ma'lumotlarini tahrirlash", callback_data="edit_anime_info")],
        [InlineKeyboardButton(text="🎞 Anime qismlarini tahrirlash", callback_data="edit_anime_episodes")]
    ])
    await message.answer("Nimani tahrirlamoqchisiz?", reply_markup=kb)

# --- Anime ma'lumotlarini tahrirlash ---
@router.callback_query(F.data == "edit_anime_info")
async def edit_anime_info_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Tahrirlamoqchi bo'lgan anime kodini yuboring:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], resize_keyboard=True))
    await state.set_state(EditAnimeState.code)
    await callback.answer()

@router.message(EditAnimeState.code)
async def edit_anime_info_code(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        return await message.answer("Bekor qilindi.", reply_markup=anime_settings_keyboard())
    
    anime = await rq.get_anime_by_code(message.text)
    if not anime:
        return await message.answer("❌ Bunday kodli anime topilmadi. Qaytadan urinib ko'ring:")
    
    await state.update_data(anime_id=anime.id, anime_name=anime.name)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Nomi", callback_data="editfield_name"),
         InlineKeyboardButton(text="Ma'lumot", callback_data="editfield_description")],
        [InlineKeyboardButton(text="Kodi", callback_data="editfield_code"),
         InlineKeyboardButton(text="Rasm (File ID)", callback_data="editfield_image_id")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="editfield_cancel")]
    ])
    
    await message.answer(f"🎬 Anime: **{anime.name}**\n\nQaysi maydonni o'zgartirmoqchisiz?", reply_markup=kb)
    await state.set_state(EditAnimeState.choice)

@router.callback_query(EditAnimeState.choice, F.data.startswith("editfield_"))
async def edit_anime_field_choice(callback: CallbackQuery, state: FSMContext):
    field = callback.data.split("_")[1]
    if field == "cancel":
        await state.clear()
        await callback.message.edit_text("Tahrirlash bekor qilindi.")
        return await callback.message.answer("Menyu:", reply_markup=anime_settings_keyboard())
    
    await state.update_data(field=field)
    await callback.message.edit_text(f"Yangi qiymatni yuboring (Hozirgi maydon: {field}):")
    await state.set_state(EditAnimeState.new_value)
    await callback.answer()

@router.message(EditAnimeState.new_value)
async def edit_anime_field_save(message: Message, state: FSMContext):
    data = await state.get_data()
    field = data['field']
    anime_id = data['anime_id']
    
    val = message.text
    if field == "image_id" and message.photo:
        val = message.photo[-1].file_id
    
    await rq.update_anime(anime_id, **{field: val})
    await message.answer(f"✅ Ma'lumot yangilandi!", reply_markup=anime_settings_keyboard())
    await state.clear()

# --- Anime qismlarini tahrirlash ---
@router.callback_query(F.data == "edit_anime_episodes")
async def edit_episodes_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Qismlarini o'zgartirmoqchi bo'lgan anime kodini yuboring:", reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Bekor qilish")]], resize_keyboard=True))
    await state.set_state(EditEpisodeState.anime_code)
    await callback.answer()

@router.message(EditEpisodeState.anime_code)
async def edit_episodes_code(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        return await message.answer("Bekor qilindi.", reply_markup=anime_settings_keyboard())
    
    anime = await rq.get_anime_by_code(message.text)
    if not anime:
        return await message.answer("❌ Bunday kodli anime topilmadi. Qaytadan urinib ko'ring:")
    
    episodes = await rq.get_episodes(anime.id)
    episodes_list = list(episodes)
    
    buttons = []
    row = []
    for ep in episodes_list:
        row.append(InlineKeyboardButton(text=f"📝 {ep.part}-qism", callback_data=f"editep_{ep.id}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(f"🎬 Anime: **{anime.name}**\n\nVideosi o'zgartirilishi kerak bo'lgan qismni tanlang:", reply_markup=keyboard)
    await state.set_state(EditEpisodeState.choice)

@router.callback_query(EditEpisodeState.choice, F.data.startswith("editep_"))
async def edit_episode_choice(callback: CallbackQuery, state: FSMContext):
    ep_id = callback.data.split("_")[1]
    await state.update_data(ep_id=ep_id)
    await callback.message.edit_text("Ushbu qism uchun yangi videoni yuboring:")
    await state.set_state(EditEpisodeState.new_video)
    await callback.answer()

@router.message(EditEpisodeState.new_video, (F.video | F.document))
async def edit_episode_save(message: Message, state: FSMContext):
    data = await state.get_data()
    ep_id = data['ep_id']
    
    if message.video:
        file_id = message.video.file_id
    elif message.document and (message.document.mime_type or "").startswith('video'):
        file_id = message.document.file_id
    else:
        return await message.answer("⚠️ Iltimos, video fayl yuboring.")
    
    await rq.update_episode(int(ep_id), file_id=file_id)
    await message.answer("✅ Video muvaffaqiyatli yangilandi!", reply_markup=anime_settings_keyboard())
    await state.clear()
