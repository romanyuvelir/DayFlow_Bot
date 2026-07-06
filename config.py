import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
DB_PATH: str = "dayflow.db"

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан! Создай файл .env и укажи токен.")
