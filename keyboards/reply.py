from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def admin_main_keyboard():
    keyboard = [
        [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="Xabar Yuborish")],
        [KeyboardButton(text="📮 Post tayyorlash"), KeyboardButton(text="📩 TEXT POST")],
        [KeyboardButton(text="🎬 Animelar sozlash")],
        [KeyboardButton(text="🔍 Foydalanuvchini boshqarish")],
        [KeyboardButton(text="📢 Kanallar"), KeyboardButton(text="📋 Adminlar")],
        [KeyboardButton(text="📝 Reklama matni")],
        [KeyboardButton(text="🤖 Bot holati")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def anime_settings_keyboard():
    keyboard = [
        [KeyboardButton(text="➕ Anime qo'shish"), KeyboardButton(text="🎞 Qisim qo'shish")],
        [KeyboardButton(text="📝 Tahrirlash"), KeyboardButton(text="🗑 O'chirish")],
        [KeyboardButton(text="🗑 Anime o'chirish")],
        [KeyboardButton(text="🔙 Orqaga")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def broadcast_type_keyboard():
    keyboard = [
        [KeyboardButton(text="📤 Copy (Asliday)"), KeyboardButton(text="🔄 Forward (Muallif bilan)")],
        [KeyboardButton(text="❌ Bekor qilish")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)



