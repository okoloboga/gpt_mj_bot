from aiogram.utils import executor
from create_bot import dp, bot
from utils import db
from handlers import admin
from handlers import users
from handlers import sub

async def on_startup(_):
    # Функция, которая выполняется при запуске бота.
    # Здесь вызывается метод start() из модуля db, который инициирует подключение к базе данных.
    await db.start()


if __name__ == "__main__":
    # Если файл запускается как основной (а не импортируется как модуль),
    # бот начинает получать и обрабатывать обновления (сообщения, команды и т.д.)
    # dp - диспетчер из create_bot, который обрабатывает входящие сообщения
    # skip_updates=True - игнорирует старые обновления, накопившиеся до запуска бота
    # on_startup=on_startup - запускает функцию при старте
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)

