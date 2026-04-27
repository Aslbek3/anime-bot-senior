import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from aiogram import Bot, Dispatcher
from data.config import BOT_TOKEN, REDIS_URL
from database.models import async_main
import database.requests as rq
from handlers.users import router as user_router
from handlers.admin import router as admin_router
from middlewares.check_sub import CheckSubMiddleware
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.storage.memory import MemoryStorage


async def main():
    await async_main()
    await rq.init_settings_cache()
    logging.info("Settings cache loaded.")

    try:
        storage = RedisStorage.from_url(REDIS_URL)
        await storage.redis.ping()
        logging.info("Redis connected successfully.")
    except Exception as e:
        logging.warning(f"Redis connection failed: {e}. Falling back to MemoryStorage.")
        storage = MemoryStorage()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=storage)

    await bot.delete_webhook(drop_pending_updates=True)

    check_sub_middleware = CheckSubMiddleware()
    dp.message.middleware(check_sub_middleware)
    dp.callback_query.middleware(check_sub_middleware)

    dp.include_router(admin_router)
    dp.include_router(user_router)

    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Error during polling: {e}")


if __name__ == "__main__":
    asyncio.run(main())
