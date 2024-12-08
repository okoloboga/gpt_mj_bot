import string
import random
import logging
from datetime import datetime, timedelta

from aiogram.types import Message, CallbackQuery
from aiogram.dispatcher import FSMContext

import config
import keyboards.admin as admin_kb  # Клавиатуры для админских команд
from config import bot_url, ADMINS
from utils.ai import mj_api
from create_bot import dp  # Диспетчер для регистрации хендлеров
from tabulate import tabulate  # Модуль для форматирования данных в таблицы
import states.admin as states  # Состояния для административных задач
from utils import db  # Модуль для работы с базой данных
import asyncio


logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(filename)s:%(lineno)d #%(levelname)-8s '
           '[%(asctime)s] - %(name)s - %(message)s')


# Фильтрация данных из статистики
def format_statistics(stats):
    result = ""
    for order_type, details in stats.items():
        # Определяем единицу измерения в зависимости от типа заказа
        unit = "запросов" if order_type == "midjourney" else "токенов"
        
        quantity_map = {
            "100000": "100к",
            "200000": "200к",
            "500000": "500к"
            }

        if quantity in quantity_map:
            quantity = quantity_map[quantity]
            
        result += f"{order_type.capitalize()}:\n" 

        for quantity, data in details.items():
            result += f"{quantity} {unit}: {data['count']}, на сумму {data['total_amount']}₽.\n"
        result += "\n"
    return result



# Хендлер для переключения основного API
@dp.message_handler(lambda message: message.from_user.id in ADMINS,
                    text=["#switch_to_goapi", "#switch_to_apiframe"]
                    )
async def switch_api_handler(message: Message):

    if message.text == "#switch_to_goapi":
        try:
            mj_api.set_primary_api("goapi")
            await message.reply("Основной API переключен на **GoAPI**.")
            logging.info(f"API переключено на GoAPI по команде пользователя {user_id}.")
        except ValueError as e:
            await message.reply(f"Ошибка: {e}")
            logging.error(f"Ошибка при переключении на GoAPI: {e}")
    elif message.text == "#switch_to_apiframe":
        try:
            mj_api.set_primary_api("apiframe")
            await message.reply("Основной API переключен на **ApiFrame**.")
            logging.info(f"API переключено на ApiFrame по команде пользователя {user_id}.")
        except ValueError as e:
            await message.reply(f"Ошибка: {e}")
            logging.error(f"Ошибка при переключении на ApiFrame: {e}")

# Хендлер для отображения статистики по пользователям и запросам
@dp.message_handler(lambda message: message.from_user.id in ADMINS,
                    commands="stats"
                    )
async def show_stats(message: Message):
    
    stats_data = await db.get_stat()  # Получаем общую статистику

    stats_24h = await db.get_orders_statistics(period="24h")
    # stats_month = await db.get_orders_statistics(period="month")
    stats_all = await db.get_orders_statistics(period="all")

    response = "📊 Статистика покупок:\n\n"

    response += "За последние 24 часа:\n\n"
    response += format_statistics(stats_24h) + "\n"

    # response += "За текущий месяц:\n\n"
    # response += format_statistics(stats_month) + "\n"

    response += "За все время:\n"
    response += format_statistics(stats_all) + "\n"

    await message.answer(f"""За все время
Количество пользователей: {stats_data['users_count']}
Запросов {stats_data['chatgpt_count'] + stats_data['image_count']}
ChatGPT - {stats_data['chatgpt_count']}
Midjourney - {stats_data['image_count']}
 
За 24 часа:
Пользователей - {stats_data['today_users_count']}
Запросов - {stats_data['today_chatgpt_count'] + stats_data['today_image_count']}
ChatGPT - {stats_data['today_chatgpt_count']}
Midjourney - {stats_data['today_image_count']}

{response}
""", reply_markup=admin_kb.admin_menu)  # Кнопки для админа


# Хендлер для отображения реферальной статистики
@dp.callback_query_handler(is_admin=True, text='admin_ref_menu')
async def admin_ref_menu(call: CallbackQuery):

    inviters_id = await db.get_all_inviters()  # Получаем всех пользователей, у которых есть рефералы
    inviters = []
    for inviter_id in inviters_id:
        inviter = await db.get_ref_stat(inviter_id['inviter_id'])  # Статистика по реферальным ссылкам
        if inviter['all_income'] is None:
            all_income = 0
        else:
            all_income = inviter['all_income']

        # Сохраняем данные по каждому рефералу
        inviters.append(
            {'user_id': inviter_id['inviter_id'], 'refs_count': inviter['count_refs'],
             'orders_count': inviter['orders_count'],
             'all_income': all_income, 'available_for_withdrawal': inviter['available_for_withdrawal']})

    # Сортируем рефералов по заработанным средствам
    sort_inviters = sorted(inviters, key=lambda d: d['all_income'], reverse=True)
    await call.message.answer(
        f'<b>Партнерская статистика</b>\n\n<pre>{tabulate(sort_inviters, tablefmt="jira", numalign="left")}</pre>')  # Таблица с данными
    await call.answer()


# Хендлер для выдачи подписки пользователю через команду
@dp.message_handler(commands="sub", is_admin=True)
async def add_balance(message: Message):

    try:
        # Парсим аргументы команды: ID пользователя и тип подписки
        user_id, sub_type = message.get_args().split(" ")
        if sub_type not in config.sub_types.keys():
            raise ValueError
        user_id = int(user_id)
    except ValueError:
        await message.answer("Команда введена неверно. Используйте /sub {id пользователя} {тип подписки}")
        return

    user = await db.get_user(user_id)  # Получаем пользователя из базы
    if not user:
        return await message.answer("Пользователь не найден")
    
    # Определяем дату окончания подписки (если текущая подписка уже истекла — начинаем с текущей даты)
    if user["sub_time"] < datetime.now():
        base_sub_time = datetime.now()
    else:
        base_sub_time = user["sub_time"]
    sub_time = base_sub_time + timedelta(days=30)  # Добавляем 30 дней подписки
    tokens = config.sub_types[sub_type]["tokens"]  # Получаем количество токенов для выбранного типа подписки
    mj = config.sub_types[sub_type]["mj"]  # Количество запросов для MidJourney
    await db.update_sub_info(user_id, sub_time, sub_type, tokens, mj)  # Обновляем данные в базе
    await message.answer('Подписка выдана')  # Подтверждение админу


# Хендлер для изменения баланса пользователя через команду
@dp.message_handler(commands="balance", is_admin=True)
async def add_balance(message: Message):

    try:
        # Парсим аргументы команды: ID пользователя и сумму изменения баланса
        user_id, value = message.get_args().split(" ")
        value = int(value)
        user_id = int(user_id)
    except ValueError:
        await message.answer("Команда введена неверно. Используйте /balance {id пользователя} {баланс}")
        return
    await db.add_balance_from_admin(user_id, value)  # Изменение баланса в базе
    await message.answer('Баланс изменён')  # Подтверждение админу


# Хендлер для запуска рассылки сообщений
@dp.message_handler(commands="send", is_admin=True)
async def enter_text(message: Message):

    await message.answer("Введите текст рассылки", reply_markup=admin_kb.cancel)  # Запрос текста для рассылки
    await states.Mailing.enter_text.set()  # Устанавливаем состояние для ввода текста


# Хендлер для отправки рассылки всем пользователям
@dp.message_handler(state=states.Mailing.enter_text, is_admin=True)
async def start_send(message: Message, state: FSMContext):

    await message.answer("Начал рассылку")
    await state.finish()  # Завершаем состояние
    users = await db.get_users()  # Получаем всех пользователей
    count = 0
    block_count = 0
    for user in users:
        try:
            await message.bot.send_message(user["user_id"], message.text)  # Отправляем сообщение каждому пользователю
            count += 1
        except:
            block_count += 1  # Считаем пользователей, заблокировавших бота
        await asyncio.sleep(0.1)  # Делаем небольшую паузу между отправками
    await message.answer(
        f"Количество получивших сообщение: {count}. Пользователей, заблокировавших бота: {block_count}")  # Итог рассылки


# Хендлер для создания промокода через команду
@dp.message_handler(commands="freemoney", is_admin=True)
async def create_promocode(message: Message):

    try:
        # Парсим аргументы команды: сумму и количество активаций промокода
        amount, uses_count = message.get_args().split(" ")
        amount = int(amount)
        uses_count = int(uses_count)
    except ValueError:
        return await message.answer("Команда введена неверно. Используйте /freemoney {сумма} {кол-во активаций}")
    
    # Генерируем случайный промокод
    code = ''.join(random.sample(string.ascii_uppercase, 10))
    await db.create_promocode(amount, uses_count, code)  # Создаем промокод в базе
    promocode_url = f"{bot_url}?start=p{code}"  # Формируем ссылку с промокодом
    await message.answer(f"Промокод создан, ссылка: {promocode_url}")  # Отправляем ссылку админу


# Хендлер для отображения статистики по промокодам через callback
@dp.callback_query_handler(is_admin=True, text='admin_promo_menu')
async def admin_promo_menu(call: CallbackQuery):
    
    promocodes = await db.get_promo_for_stat()  # Получаем статистику по промокодам
    # Формируем таблицу с промокодами
    await call.message.answer(
        f'<b>Бонус ссылки</b>\n\n<pre>{tabulate(promocodes, tablefmt="jira", numalign="left")}</pre>')
    await call.answer()
