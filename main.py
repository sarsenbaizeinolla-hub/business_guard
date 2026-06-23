import asyncio
import logging
import aiosqlite
import aiohttp
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

# Загружаем переменные из .env
load_dotenv()
TOKEN = os.getenv("TOKEN")

# Настройка логирования
logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Инициализация БД
async def init_db():
    async with aiosqlite.connect("sites.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                url TEXT
            )
        """)
        await db.commit()

# Команда /start
@dp.message(Command("start"))
async def start(message: Message):
    await message.answer("Привет! Я бот для мониторинга сайтов. Используй /add <ссылка>, /list и /delete <ссылка>.")

# Добавление сайта
@dp.message(Command("add"))
async def add_site(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Укажи ссылку. Пример: /add https://google.com")
        return
    
    url = args[1]
    user_id = message.from_user.id
    
    async with aiosqlite.connect("sites.db") as db:
        await db.execute("INSERT INTO sites (user_id, url) VALUES (?, ?)", (user_id, url))
        await db.commit()
    await message.answer(f"✅ Сайт {url} успешно добавлен.")

# Список сайтов пользователя
@dp.message(Command("list"))
async def list_sites(message: Message):
    user_id = message.from_user.id
    async with aiosqlite.connect("sites.db") as db:
        async with db.execute("SELECT url FROM sites WHERE user_id = ?", (user_id,)) as cursor:
            sites = await cursor.fetchall()
            if sites:
                text = "🌐 Твои сайты:\n" + "\n".join([s[0] for s in sites])
            else:
                text = "У тебя пока нет добавленных сайтов."
            await message.answer(text)

# Удаление сайта
@dp.message(Command("delete"))
async def delete_site(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Укажи ссылку для удаления. Пример: /delete https://google.com")
        return
    
    url = args[1]
    user_id = message.from_user.id
    
    async with aiosqlite.connect("sites.db") as db:
        await db.execute("DELETE FROM sites WHERE user_id = ? AND url = ?", (user_id, url))
        await db.commit()
    await message.answer(f"🗑 Сайт {url} удален.")

# Фоновый мониторинг
async def monitor_sites():
    while True:
        async with aiosqlite.connect("sites.db") as db:
            async with db.execute("SELECT user_id, url FROM sites") as cursor:
                sites = await cursor.fetchall()
        
        async with aiohttp.ClientSession() as session:
            for user_id, url in sites:
                try:
                    async with session.get(url, timeout=10) as response:
                        if response.status != 200:
                            await bot.send_message(user_id, f"⚠️ Сайт {url} вернул статус {response.status}")
                except Exception as e:
                    await bot.send_message(user_id, f"❌ Сайт {url} недоступен! Ошибка: {str(e)[:30]}")
        
        await asyncio.sleep(60) # Проверка каждую минуту

# Основной запуск
async def main():
    await init_db()
    asyncio.create_task(monitor_sites())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())