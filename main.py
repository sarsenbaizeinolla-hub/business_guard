import asyncio
import aiosqlite
import aiohttp
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Твой токен от BotFather
TOKEN = "8629717626:AAHx0iZ1Vc5PJltcFEafMo0XTfRD80ozlhA"
# Твой ID, который прислал @userinfobot
MY_ID = "7873130977" 

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

async def init_db():
    async with aiosqlite.connect("sites.db") as db:
        await db.execute("CREATE TABLE IF NOT EXISTS sites (url TEXT)")
        await db.commit()

# Функция, которая будет проверять сайты в фоне
async def monitor_sites():
    while True:
        async with aiosqlite.connect("sites.db") as db:
            async with db.execute("SELECT url FROM sites") as cursor:
                sites = await cursor.fetchall()
        
        if sites:
            async with aiohttp.ClientSession() as session:
                for site in sites:
                    url = site[0]
                    try:
                        async with session.get(url, timeout=10) as response:
                            if response.status != 200:
                                await bot.send_message(MY_ID, f"⚠️ Сайт {url} вернул статус {response.status}")
                    except Exception as e:
                        await bot.send_message(MY_ID, f"❌ Сайт {url} недоступен! Ошибка: {str(e)[:50]}")
        
        # Проверка каждые 60 секунд
        await asyncio.sleep(60)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Бот мониторинга активен! Используй /add <ссылка> для добавления сайтов.")

@dp.message(Command("add"))
async def add_site(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Укажи ссылку. Пример: /add https://google.com")
        return
    
    url = args[1]
    async with aiosqlite.connect("sites.db") as db:
        await db.execute("INSERT INTO sites (url) VALUES (?)", (url,))
        await db.commit()
    await message.answer(f"✅ Сайт {url} добавлен в мониторинг.")

@dp.message(Command("list"))
async def list_sites(message: types.Message):
    async with aiosqlite.connect("sites.db") as db:
        async with db.execute("SELECT url FROM sites") as cursor:
            sites = await cursor.fetchall()
            text = "🌐 Мониторинг:\n" + "\n".join([s[0] for s in sites]) if sites else "Список пуст."
            await message.answer(text)

async def main():
    await init_db()
    # Запускаем мониторинг как фоновую задачу
    asyncio.create_task(monitor_sites())
    print("Бот и монитор успешно запущены...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nБот остановлен.")