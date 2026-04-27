from os import getenv
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = getenv("BOT_TOKEN")
ADMINS = list(map(int, getenv("ADMINS", "").split(","))) if getenv("ADMINS") else []
DB_URL = getenv("DB_URL") # postgresql+asyncpg://user:password@localhost/dbname
REDIS_URL = getenv("REDIS_URL", "redis://localhost:6379/0")
