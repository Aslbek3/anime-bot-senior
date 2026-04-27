from typing import Callable, Dict, Any, Awaitable, Union
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database.requests import get_channels, add_user
from data.config import ADMINS

class CheckSubMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Union[Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any]
    ) -> Any:
        if not event.from_user:
            return await handler(event, data)
        
        # Foydalanuvchini bazaga qo'shish (faqat xabar bo'lganda yoki har doim)
        if isinstance(event, Message):
            await add_user(event.from_user.id, event.from_user.full_name, event.from_user.username)
        
        # Admin bo'lsa tekshirmaymiz
        if event.from_user.id in ADMINS:
            return await handler(event, data)

        channels = await get_channels()
        not_subbed = []
        
        for channel in channels:
            try:
                member = await event.bot.get_chat_member(channel.channel_id, event.from_user.id)
                # Faqat member, administrator yoki creator bo'lsa o'tkazamiz
                if member.status not in ["member", "administrator", "creator"]:
                    not_subbed.append(channel)
            except Exception:
                continue
        
        if not_subbed:
            buttons = []
            for channel in not_subbed:
                buttons.append([InlineKeyboardButton(text=channel.title, url=channel.invite_link)])
            
            buttons.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            text = "❌ Botdan foydalanish uchun quyidagi kanallarga a'zo bo'lishingiz kerak:"
            
            if isinstance(event, Message):
                return await event.answer(text, reply_markup=keyboard)
            else:
                # Callback bo'lsa, ogohlantirish chiqaramiz yoki xabarni o'zgartiramiz
                return await event.message.answer(text, reply_markup=keyboard)
        
        return await handler(event, data)
