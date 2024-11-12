import logging
from datetime import datetime, timedelta
from typing import List

import requests
from aiogram import Bot
from aiogram.types import Message, CallbackQuery, ChatActions, ContentType
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher import FSMContext

import config
from utils import db, ai, more_api, pay  # Импорт утилит для взаимодействия с БД и внешними API
from states import user as states  # Состояния FSM для пользователя
import keyboards.user as user_kb  # Клавиатуры для взаимодействия с пользователями
from config import bot_url, TOKEN, NOTIFY_URL, bug_id, PHOTO_PATH, MJ_PHOTO_BASE_URL
from create_bot import dp  # Диспетчер из create_bot.py
from utils.ai import mj_api

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(filename)s:%(lineno)d #%(levelname)-8s '
           '[%(asctime)s] - %(name)s - %(message)s')

vary_types = {"subtle": "Subtle", "strong": "Strong"}  # Типы для использования в дальнейшем

'''
# Проверка и активация промокодов
async def check_promocode(user_id, code, bot: Bot):

    promocode = await db.get_promocode_by_code(code)  # Получаем промокод по коду
    if promocode is None:
        return
    # Проверяем, использовал ли пользователь этот промокод ранее
    user_promocode = await db.get_user_promocode_by_promocode_id_and_user_id(promocode["promocode_id"], user_id)
    all_user_promocode = await db.get_all_user_promocode_by_promocode_id(promocode["promocode_id"])
    
    # Если пользователь не использовал промокод и есть свободные активации, применяем его
    if user_promocode is None and len(all_user_promocode) < promocode["uses_count"]:
        await db.create_user_promocode(promocode["promocode_id"], user_id)
        await db.add_balance(user_id, promocode['amount'], is_promo=True)  # Пополняем баланс на сумму промокода
        await bot.send_message(user_id, f"<b>Баланс пополнен на {promocode['amount']} рублей.</b>")
    else:
        # Уведомление, если промокод уже использован или исчерпаны активации
        if user_promocode is not None:
            await bot.send_message(user_id, "<b>Данная ссылка была активирована Вами ранее.</b>")
        elif len(all_user_promocode) >= promocode["uses_count"]:
            await bot.send_message(user_id, "<b>Ссылка исчерпала максимальное количество активаций.</b>")
'''

# Снижение баланса пользователя
async def remove_balance(bot: Bot, user_id):

    await db.remove_balance(user_id)
    user = await db.get_user(user_id)
    # Если баланс меньше 50, отправляем уведомление о необходимости пополнения
    if user["balance"] <= 50:
        await db.update_stock_time(user_id, int(datetime.now().timestamp()))
        await bot.send_message(user_id, """⚠️Заканчивается баланс!
Успей пополнить в течении 24 часов и получи на счёт +10% от суммы пополнения ⤵️""", 
                               reply_markup=user_kb.get_pay(user_id, 10))  # Кнопка пополнения баланса

'''
# Тексты для разных типов подписок
sub_types_texts = {
    "standard": """Тариф <b>«Стандарт»</b>
2 млн токенов для ChatGPT
20 запросов в Midjourney в день""",
    "premium": """Тариф <b>«Премиум»</b>
5 млн токенов для ChatGPT
40 запросов в Midjourney в день""",
    "illustrator": """Тариф <b>«Иллюстратор»</b>
50 тыс токенов для ChatGPT
100 запросов в Midjourney в день""",
    "author": """Тариф <b>«Автор»</b>
10 млн токенов для ChatGPT
5 запросов в Midjourney в день"""
}


# Уведомление о недостатке средств на балансе
async def not_enough_balance(bot: Bot, user_id, ai_type="chatgpt"):

    text = """К сожалению ваш суточный лимит исчерпан
Вы можете выбрать тариф с бо́льшим количество запросов⤵️\n\n"""
    user = await db.get_user(user_id)
    if user["sub_time"] and user["sub_time"] < datetime.now():
        # Уведомление о необходимости подписки, если лимит исчерпан
        if ai_type == "chatgpt":
            text = """К сожалению лимит запросов исчерпан
Больше запросов для ChatGPT доступно по подписке⤵️"""
        else:
            text = """К сожалению лимит запросов исчерпан
Больше запросов для Midjourney доступно по подписке⤵️"""
        kb = user_kb.top_up_balance  # Кнопка для пополнения баланса
    else:
        showed_sub_types = ()
        if user["sub_type"] == "base":
            showed_sub_types = ("standard", "premium", "illustrator", "author")
        elif user["sub_type"] == "standard":
            showed_sub_types = ("premium", "illustrator", "author")
        elif user["sub_type"] == "premium":
            showed_sub_types = ("illustrator", "author")
        for sub_type in showed_sub_types:
            text += f"{sub_types_texts[sub_type]}\n\n"
        kb = user_kb.top_up_balance  # Кнопка для пополнения
        if user["sub_type"] in ("illustrator", "author"):
            kb = None  # Для этих типов тарифов кнопка пополнения не нужна
            text = "К сожалению ваш суточный лимит исчерпан"
    await bot.send_message(user_id, text, reply_markup=kb)
'''


# Функция для уведомления пользователя о недостатке средств
async def not_enough_balance(bot: Bot, user_id: int, ai_type: str):

    now = datetime.now()

    if ai_type == "chatgpt":
        user_data = await db.get_user_notified_gpt(user_id)

        if user_data and user_data['last_notification']:
            last_notification = user_data['last_notification']

            # Если уведомление было менее 24 часов назад, показываем меню со скидкой
            if now < last_notification + timedelta(hours=24):
                await bot.send_message("""
К сожалению, лимит токенов для 💬ChatGPT исчерпан
Вы можете восполнить токены по кнопке⤵️
                """,
                    reply_markup=user_kb.get_сhatgpt_discount_tokens_menu()
                )
                return

        await bot.send_message(user_id, """
К сожалению, лимит токенов для 💬ChatGPT исчерпан
Вы можете восполнить токены по кнопке⤵️
        """, reply_markup=user_kb.get_chatgpt_tokens_menu())  # Отправляем уведомление с клавиатурой для пополнения токенов

    elif ai_type == "image":
        user_data = await db.get_user_notified_mj(user_id)

        if user_data and user_data['last_notification']:
            last_notification = user_data['last_notification']

            # Если уведомление было менее 24 часов назад, показываем меню со скидкой
            if now < last_notification + timedelta(hours=24):
                await bot.send_message("""
К сожалению, лимит запросов для 
🎨Midjourney исчерпан
Вы можете восполнить запросы по кнопке⤵️
                """,
                    reply_markup=user_kb.get_midjourney_discount_requests_menu()
                )
                return
        await bot.send_message(user_id, """
К сожалению, лимит запросов для 
🎨Midjourney исчерпан
Вы можете восполнить запросы по кнопке⤵️
        """, reply_markup=user_kb.get_midjourney_requests_menu())  # Отправляем уведомление с клавиатурой для пополнения запросов


# Генерация изображения через MidJourney
async def get_mj(prompt, user_id, bot: Bot):

    user = await db.get_user(user_id)

    # Проверяем наличие запросов и отправляем уведомление, если запросы исчерпаны
    if user["mj"] <= 0 and user["free_image"] <= 0:
        await not_enough_balance(bot, user_id, "image")  # Отправляем уведомление о недостатке средств
        return

    await bot.send_message(user_id, "Ожидайте, генерирую изображение..🕙", reply_markup=user_kb.get_menu(user["default_ai"]))
    await bot.send_chat_action(user_id, ChatActions.UPLOAD_PHOTO)

    res = await ai.get_mdjrny(prompt, user_id)  # Получаем изображение через API

    logger.info(f"MidJourney: {res}")

    if res is None:
        await bot.send_message(user_id, f"Произошла ошибка, повторите попытку позже")
        return
    elif res['status'] == "failed":
        await bot.send_message(user_id, f"Произошла ошибка, подробности ошибки:\n\n{res['message']}")
        return

    # Проверка на количество оставшихся запросов MidJourney
    now = datetime.now()
    user_notified = await db.get_user_notified_mj(user_id)
    user = await db.get_user(user_id)  # Получаем обновленные данные пользователя
    
    if 1 < user["mj"] <= 3:  # Если осталось 3 или меньше запросов
        if user_notified is None:
            await db.create_user_notification_mj(user_id)
            await notify_low_midjourney_requests(user_id, bot)  # Отправляем уведомление о низком количестве токенов
            # await db.set_user_notified(user_id)  # Помечаем, что уведомление отправлено
        else:
            last_notification = user_notified['last_notification']
            if last_notification is None or now > last_notification + timedelta(days=30):
                await db.update_user_notification_mj(user_id)
                await notify_low_midjourney_requests(user_id, bot)


# Генерация ответа от ChatGPT
async def get_gpt(prompt, messages, user_id, bot: Bot):

    user = await db.get_user(user_id)
    lang_text = {"en": "compose an answer in English", "ru": "составь ответ на русском языке"}
    prompt += f"\n{lang_text[user['chat_gpt_lang']]}"
    messages.append({"role": "user", "content": prompt})

    await bot.send_chat_action(user_id, ChatActions.TYPING)

    res = await ai.get_gpt(messages)  # Отправляем запрос в ChatGPT
    await bot.send_message(user_id, res["content"], reply_markup=user_kb.clear_content)
    if not res["status"]:
        return
    messages.append({"role": "assistant", "content": res["content"]})

    # Списывание токенов
    if user["free_chatgpt"] > 0:
        await db.remove_free_chatgpt(user_id, res["tokens"])  # Уменьшаем бесплатные токены
    else:
        await db.remove_chatgpt(user_id, res["tokens"])  # Уменьшаем платные токены

    # Проверка на количество оставшихся токенов
    now = datetime.now()
    user_notified = await db.get_user_notified_gpt(user_id)
    user = await db.get_user(user_id)  # Получаем обновленные данные пользователя
    
    if 0 < user["tokens"] <= 30000:  # Если осталось 30 тыс или меньше токенов
        if user_notified is None:
            await db.create_user_notification_gpt(user_id)
            await notify_low_chatgpt_tokens(user_id, bot)  # Отправляем уведомление о низком количестве токенов
            # await db.set_user_notified(user_id)  # Помечаем, что уведомление отправлено
        else:
            last_notification = user_notified['last_notification']
            if last_notification is None or now > last_notification + timedelta(days=30):
                await db.update_user_notification_gpt(user_id)
                await notify_low_chatgpt_tokens(user_id, bot)

    await db.add_action(user_id, "chatgpt")  # Логируем действие пользователя
    return messages


''' Новые две функции - уведомления об заканчивающихся токенах '''

# Уведомение о низком количестве токенов GPT
async def notify_low_chatgpt_tokens(user_id, bot: Bot):

    await bot.send_message(user_id, """
У вас заканчиваются токены для 💬ChatGPT
Специально для вас мы подготовили <b>персональную скидку</b>!

Успейте приобрести токены со скидкой, предложение актуально <b>24 часа</b>⤵️
    """, reply_markup=user_kb.get_chatgpt_discount_nofication())

# Уведомление о низком количестве запросов MidJourney
async def notify_low_midjourney_requests(user_id, bot: Bot):

    await bot.send_message(user_id, """
У вас заканчиваются запросы для 🎨Midjourney
Специально для вас мы подготовили <b>персональную скидку</b>!

Успейте приобрести запросы со скидкой, предложение актуально <b>24 часа</b>⤵️
    """, reply_markup=user_kb.get_midjourney_discount_notification())


# Хэндлер команды /start
@dp.message_handler(state="*", commands='start')
async def start_message(message: Message, state: FSMContext):

    await state.finish()  # Завершаем любое текущее состояние

    # Обрабатываем параметры команды /start (например, реферальные коды)
    msg_args = message.get_args().split("_")
    inviter_id = 0
    code = None
    if msg_args != ['']:
        for msg_arg in msg_args:
            if msg_arg[0] == "r":
                try:
                    inviter_id = int(msg_arg[1:])
                except ValueError:
                    continue
            elif msg_arg[0] == "p":
                code = msg_arg[1:]

    user = await db.get_user(message.from_user.id)

    if user is None:
        await db.add_user(message.from_user.id, message.from_user.username, message.from_user.first_name, int(inviter_id))
        default_ai = "chatgpt"
    else:
        default_ai = user["default_ai"]

    # Отправляем приветственное сообщение
    await message.answer("""<b>NeuronAgent</b>🤖 - <i>2 нейросети в одном месте!</i>
<b>ChatGPT или Midjourney?</b>""", reply_markup=user_kb.get_menu(default_ai))

    # Проверка промокода, если он был передан
    if code is not None:
        await check_promocode(message.from_user.id, code, message.bot)



# Хендлер для проверки подписки через callback-запрос
@dp.callback_query_handler(text="check_sub")
async def check_sub(call: CallbackQuery):

    user = await db.get_user(call.from_user.id)  # Получаем данные пользователя из базы
    if user is None:
        # Если пользователь новый, создаем запись
        await db.add_user(call.from_user.id, call.from_user.username, call.from_user.first_name, 0)
    await call.message.answer("""<b>NeuronAgent</b>🤖 - <i>2 нейросети в одном месте!</i>

<b>ChatGPT или Midjourney?</b>""", reply_markup=user_kb.get_menu(user["default_ai"]))  # Меню выбора AI
    await call.answer()


# Хендлер для удаления сообщения через callback-запрос
@dp.callback_query_handler(text="delete_msg")
async def delete_msg(call: CallbackQuery, state: FSMContext):

    await call.message.delete()  # Удаляем сообщение


# Хендлер для возврата к главному меню через callback-запрос
@dp.callback_query_handler(text="back_to_menu")
async def back_to_menu(call: CallbackQuery):

    user = await db.get_user(call.from_user.id)  # Получаем данные пользователя
    await call.message.answer("""NeuronAgent🤖 - 2 нейросети в одном месте!

ChatGPT или Midjourney?""", reply_markup=user_kb.get_menu(user["default_ai"]))  # Меню выбора AI
    await call.message.delete()  # Удаляем предыдущее сообщение

# Хендлер для партнерской программы
@dp.message_handler(text="🤝Партнерская программа")
@dp.message_handler(commands='partner')
async def ref_menu(message: Message):

    ref_data = await db.get_ref_stat(message.from_user.id)  # Получаем данные по рефералам
    if ref_data['all_income'] is None:
        all_income = 0
    else:
        all_income = ref_data['all_income']
    
    # Отправляем пользователю QR-код и информацию о партнерской программе
    await message.answer_photo(more_api.get_qr_photo(bot_url + '?start=' + str(message.from_user.id)),
                               caption=f'''<b>🤝 Партнёрская программа</b>

<i>Приводи друзей и зарабатывай 15% с их пополнений, пожизненно!</i>

<b>⬇️ Твоя реферальная ссылка:</b>
└ {bot_url}?start=r{message.from_user.id}

<b>🏅 Статистика:</b>
├ Лично приглашённых: <b>{ref_data["count_refs"]}</b>
├ Количество оплат: <b>{ref_data["orders_count"]}</b>
├ Всего заработано: <b>{int(all_income * 0.15)}</b> рублей
└ Доступно к выводу: <b>{ref_data["available_for_withdrawal"]}</b> рублей

Ваша реферальная ссылка: ''',
                               reply_markup=user_kb.get_ref_menu(f'{bot_url}?start=r{message.from_user.id}'))

# Хендлер для показа профиля пользователя (страница аккаунта)
@dp.message_handler(state="*", text="⚙Аккаунт")
@dp.message_handler(state="*", commands="account")
async def show_profile(message: Message, state: FSMContext):

    await state.finish()
    user = await db.get_user(message.from_user.id)  # Получаем данные пользователя

    mj = int(user['mj']) + int(user['free_image']) if int(user['mj']) + int(user['free_image']) >= 0 else 0
    gpt = int(user['tokens']) + int(user['free_chatgpt']) if int(user['tokens']) + int(user['free_chatgpt']) >= 0 else 0

    # Формируем текст с количеством доступных генераций и токенов
    sub_text = f"""
Доступно генераций для 🎨Midjourney:  {format(mj, ',').replace(',', ' ')}
Доступно токенов для 💬ChatGPT:  {format(gpt, ',').replace(',', ' ')}
        """
    
    # Отправляем сообщение с обновленными данными аккаунта
    await message.answer(f"""🆔: <code>{message.from_user.id}</code>
{sub_text}""", reply_markup=user_kb.get_account(user["chat_gpt_lang"], "account"))

''' Старая функция для показа профиля пользователя

# Хендлер для показа профиля пользователя (страница аккаунта)
@dp.message_handler(state="*", text="⚙Аккаунт")
async def show_profile(message: Message, state: FSMContext):
    await state.finish()
    user = await db.get_user(message.from_user.id)  # Получаем данные пользователя
    sub_text = "У вас нет активной подписки"
    if user["sub_type"] and user["sub_time"] > datetime.now():
        sub_text = "Действующий тариф - " + config.sub_types[user["sub_type"]]["title"]  # Отображение текущей подписки
    await message.answer(f"""🆔: <code>{message.from_user.id}</code>
{sub_text}""", reply_markup=user_kb.get_account(user["chat_gpt_lang"], "account"))
'''


# Хендлер для возврата к профилю пользователя через callback-запрос
@dp.callback_query_handler(Text(startswith="back_to_profile"))
async def back_to_profile(call: CallbackQuery, state: FSMContext):

    src = call.data.split(":")[1]

    if src == "acc":
        await state.finish()
        user = await db.get_user(call.from_user.id)  # Получаем данные пользователя

        # Формируем текст с количеством доступных генераций и токенов
        sub_text = f"""
Доступно генераций для 🎨Midjourney:  {format(int(user['mj']) + int(user['free_image']), ',').replace(',', ' ')}
Доступно токенов для 💬ChatGPT:  {format(int(user['tokens']) + int(user['free_chatgpt']), ',').replace(',', ' ')}
        """
    
        # Отправляем сообщение с обновленными данными аккаунта
        await call.message.edit_text(f"""🆔: <code>{call.from_user.id}</code>
    {sub_text}""", reply_markup=user_kb.get_account(user["chat_gpt_lang"], "account"))

    else:
        await state.finish()

        if src == "not_gpt":
        
            await call.message.edit_text("""
У вас заканчиваются токены для 💬ChatGPT
Специально для вас мы подготовили <b>персональную скидку</b>!

Успейте приобрести токены со скидкой, предложение актуально <b>24 часа</b>⤵️
            """, reply_markup=user_kb.get_chatgpt_discount_nofication())

        if src == "not_mj":
            await call.message.edit_text("""
У вас заканчиваются запросы для 🎨Midjourney
Специально для вас мы подготовили <b>персональную скидку</b>!

Успейте приобрести запросы со скидкой, предложение актуально <b>24 часа</b>⤵️
            """, reply_markup=user_kb.get_midjourney_discount_notification())

    await call.answer()
    

# Хендлер для смены языка через callback-запрос
@dp.callback_query_handler(Text(startswith="change_lang:"))
async def change_lang(call: CallbackQuery):

    curr_lang = call.data.split(":")[1]  # Текущий язык
    from_msg = call.data.split(":")[2]  # Источник сообщения (откуда был вызван callback)
    new_lang = "en" if curr_lang == "ru" else "ru"  # Смена языка
    await db.change_chat_gpt_lang(call.from_user.id, new_lang)  # Обновляем язык в базе
    lang_text = {"ru": "русский", "en": "английский"}
    await call.answer(f"Язык изменён на {lang_text[new_lang]}")
    if from_msg == "chatgpt_menu":
        kb = user_kb.get_chat_gpt_keyboard(new_lang, from_msg)  # Меню ChatGPT
    else:
        kb = user_kb.get_account(new_lang, from_msg)  # Меню аккаунта
    await call.message.edit_reply_markup(reply_markup=kb)  # Обновляем клавиатуру


'''
# Хендлер для выбора суммы пополнения
@dp.callback_query_handler(text="top_up_balance")
async def choose_amount(call: CallbackQuery):

    await call.message.edit_text("Выберите сумму пополнения", reply_markup=user_kb.get_pay(call.from_user.id))  # Меню оплаты


# Хендлер для возврата к выбору суммы пополнения через callback-запрос
@dp.callback_query_handler(text="back_to_choose_balance", state="*")
async def back_to_choose_balance(call: CallbackQuery):

    await call.message.edit_text("Выберите сумму пополнения", reply_markup=user_kb.get_pay(call.from_user.id))  # Меню оплаты


# Хендлер для ввода другой суммы пополнения через callback-запрос
@dp.callback_query_handler(text="other_amount")
async def enter_other_amount(call: CallbackQuery):

    await call.message.edit_text("""Введите сумму пополнения баланса в рублях:

<b>Минимальный платеж 200 рублей</b>""", reply_markup=user_kb.back_to_choose)  # Меню с кнопкой "Назад"
    await states.EnterAmount.enter_amount.set()  # Устанавливаем состояние для ввода суммы
'''

# Хендлер для ChatGPT
@dp.message_handler(state="*", text="💬ChatGPT✅")
@dp.message_handler(state="*", text="💬ChatGPT")
@dp.message_handler(state="*", commands="chatgpt")
async def ask_question(message: Message, state: FSMContext):

    await state.finish()  # Завершаем текущее состояние
    await db.change_default_ai(message.from_user.id, "chatgpt")  # Устанавливаем ChatGPT как основной AI
    user = await db.get_user(message.from_user.id)  # Получаем данные пользователя

    # Проверяем наличие токенов и подписки
    if user["tokens"] <= 0 and user["free_chatgpt"] <= 0:
        return await not_enough_balance(message.bot, message.from_user.id, "chatgpt")  # Сообщаем об исчерпании лимита

    # Сообщение с запросом ввода
    await message.answer("""<b>Введите запрос</b>
Например: <code>Напиши сочинение на тему: Как я провёл это лето</code>

<u><a href="https://telegra.ph/Kak-polzovatsya-ChatGPT-podrobnaya-instrukciya-06-04">Подробная инструкция.</a></u>""",
                         reply_markup=user_kb.get_chat_gpt_keyboard(user["chat_gpt_lang"], "chatgpt_menu"),
                         disable_web_page_preview=True)


# Хендлер для вывода информации о поддержке
@dp.message_handler(state="*", text="👨🏻‍💻Поддержка")
@dp.message_handler(state="*", commands="help")
async def support(message: Message, state: FSMContext):
    
    await state.finish()  # Завершаем текущее состояние
    await message.answer('Ответы на многие вопросы можно найти в нашем <a href="https://t.me/NeuronAgent">канале</a>.',
                         disable_web_page_preview=True, reply_markup=user_kb.about)  # Кнопка с инструкцией


# Хендлер для MidJourney
@dp.message_handler(state="*", text="🎨Midjourney✅")
@dp.message_handler(state="*", text="🎨Midjourney")
@dp.message_handler(state="*", commands="midjourney")
async def gen_img(message: Message, state: FSMContext):

    await state.finish()  # Завершаем текущее состояние
    await db.change_default_ai(message.from_user.id, "image")  # Устанавливаем MidJourney как основной AI
    user = await db.get_user(message.from_user.id)  # Получаем данные пользователя
    # Проверяем наличие токенов и подписки
    if user["mj"] <= 0 and user["free_image"] <= 0:
        await not_enough_balance(message.bot, message.from_user.id, "image")  # Сообщаем об исчерпании лимита
        return

    # Сообщение с запросом ввода
    await message.answer("""<b>Введите запрос для генерации изображения</b>
<i>Например:</i> <code>Замерзшее бирюзовое озеро вокруг заснеженных горных вершин</code>

<u><a href="https://telegra.ph/Kak-polzovatsya-MidJourney-podrobnaya-instrukciya-10-16">Подробная инструкция.</a></u>""",
                         reply_markup=user_kb.get_menu("image"),
                         disable_web_page_preview=True)


# Хендлер для выбора суммы через callback-запрос
@dp.callback_query_handler(Text(startswith="select_amount"))
async def select_amount(call: CallbackQuery):

    amount = int(call.data.split(":")[1])  # Получаем сумму из callback
    # Генерация ссылок для пополнения
    urls = {
        "tinkoff": pay.get_pay_url_tinkoff(call.from_user.id, amount),
        "freekassa": pay.get_pay_url_freekassa(call.from_user.id, amount),
        "payok": pay.get_pay_url_payok(call.from_user.id, amount),
    }
    await call.message.answer(f"""💰 Сумма: <b>{amount} рублей

♻️ Средства зачислятся автоматически</b>""", reply_markup=user_kb.get_pay_urls(urls))  # Кнопки с ссылками на оплату
    await call.answer()


'''
# Хендлер для ввода суммы пополнения
@dp.message_handler(state=states.EnterAmount.enter_amount)
async def create_other_order(message: Message, state: FSMContext):

    try:
        amount = int(message.text)  # Проверка, что введено число
    except ValueError:
        await message.answer("Введите целое число!")
        return
    if amount < 10:
        await message.answer("Минимальная сумма платежа 200 рублей")
    else:
        # Генерация ссылок для пополнения
        urls = {
            "tinkoff": pay.get_pay_url_tinkoff(message.from_user.id, amount),
            "freekassa": pay.get_pay_url_freekassa(message.from_user.id, amount),
            "payok": pay.get_pay_url_payok(message.from_user.id, amount),
        }
        await message.answer(f"""💰 Сумма: <b>{amount} рублей

♻️ Средства зачислятся автоматически</b>""", reply_markup=user_kb.get_pay_urls(urls))  # Кнопки с ссылками на оплату
        await state.finish()  # Завершаем состояние
'''


# Хендлер для отмены текущего состояния
@dp.message_handler(state="*", text="Отмена")
async def cancel(message: Message, state: FSMContext):

    await state.finish()  # Завершаем текущее состояние
    user = await db.get_user(message.from_user.id)  # Получаем данные пользователя
    await message.answer("Ввод остановлен", reply_markup=user_kb.get_menu(user["default_ai"]))  # Возвращаем меню


# Хендлер для выбора изображения через callback
@dp.callback_query_handler(Text(startswith="choose_image:"))
async def choose_image(call: CallbackQuery):

    await call.answer()  # Закрываем callback уведомление
    user = await db.get_user(call.from_user.id)
    if user["mj"] <= 0 and user["free_image"] <= 0:
        await not_enough_balance(call.bot, call.from_user.id, "image")  # Проверка наличия баланса для MidJourney
        return
    task_id = call.data.split(":")[1]
    image_id = call.data.split(":")[2]
    await call.message.answer("Ожидайте, сохраняю изображение в отличном качестве…⏳", 
                              reply_markup=user_kb.get_menu(user["default_ai"]))
    res = await ai.get_choose_mdjrny(task_id, image_id, call.from_user.id)  # Запрос к MidJourney API
    if not res["success"]:
        if res["message"] == "repeat task":
            return await call.message.answer("Вы уже сохраняли это изображение!")  # Сообщение, если изображение уже сохранялось


# Хендлер для изменения изображения через callback
@dp.callback_query_handler(Text(startswith="change_image:"))
async def change_image(call: CallbackQuery):

    await call.answer()  # Закрываем callback уведомление
    user_id = call.from_user.id
    user_notified = await db.get_user_notified_mj(user_id)

    user = await db.get_user(user_id)
    if user["mj"] <= 0 and user["free_image"] <= 0:
        await not_enough_balance(call.bot, user_id, "image")  # Проверка лимитов
        return
    task_id = call.data.split(":")[3]
    button_type = call.data.split(":")[1]
    value = call.data.split(":")[2]
    await call.message.answer("Ожидайте, обрабатываю изображение⏳", 
                              reply_markup=user_kb.get_menu(user["default_ai"]))

    action_id = await db.add_action(user_id, "image", button_type)

    if 1 < user["mj"] <= 3:  # Если осталось 3 или меньше запросов
        now = datetime.now()

        if user_notified is None:
            await db.create_user_notification_mj(user_id)
            await notify_low_midjourney_requests(user_id, call.bot)  # Отправляем уведомление о низком количестве токенов
            # await db.set_user_notified(user_id)  # Помечаем, что уведомление отправлено
        else:
            last_notification = user_notified['last_notification']
            if last_notification is None or now > last_notification + timedelta(days=30):
                await db.update_user_notification_mj(user_id)
                await notify_low_midjourney_requests(user_id, call.bot)

    if button_type == "zoom":
        response = await mj_api.outpaint(task_id, value, action_id)  # Масштабирование изображения через API
    elif button_type == "vary":
        value += "_variation"
        response = await mj_api.variation(task_id, value, action_id)  # Вариация изображения через API


# Хендлер для очистки контента через callback
@dp.callback_query_handler(text="clear_content")
async def clear_content(call: CallbackQuery, state: FSMContext):

    user = await db.get_user(call.from_user.id)
    await state.finish()  # Завершаем текущее состояние
    await call.message.answer("Диалог завершен", reply_markup=user_kb.get_menu(user["default_ai"]))  # Сообщение о завершении диалога
    try:
        await call.answer()  # Закрываем callback уведомление
    except:
        pass


# Хендлер для повторного ввода запроса через callback
@dp.callback_query_handler(Text(startswith="try_prompt"))
async def try_prompt(call: CallbackQuery, state: FSMContext):

    data = await state.get_data()
    if "prompt" not in data:
        await call.message.answer("Попробуйте заново ввести запрос")
        return await call.answer()  # Закрываем callback уведомление
    await call.answer()

    user = await db.get_user(call.from_user.id)
    if user["default_ai"] == "image":
        await get_mj(data['prompt'], call.from_user.id, call.bot)  # Генерация изображения


# Хендлер для настроек ChatGPT: ввод данных о пользователе через callback
@dp.callback_query_handler(text="chatgpt_about_me", state="*")
async def chatgpt_about_me(call: CallbackQuery, state: FSMContext):

    user = await db.get_user(call.from_user.id)
    await call.message.answer(
        '<b>Введите запрос</b>\n\nПоделитесь с ChatGPT любой информацией о себе, чтобы получить более качественные ответы⤵️\n\n<u><a href="https://telegra.ph/Tonkaya-nastrojka-ChatGPT-06-30">Инструкция.</a></u>',
        disable_web_page_preview=True,
        reply_markup=user_kb.get_menu(user["default_ai"]))
    await state.set_state(states.ChangeChatGPTAboutMe.text)  # Устанавливаем состояние ввода данных
    await call.answer()


# Хендлер для сохранения введенной информации о пользователе в ChatGPT
@dp.message_handler(state=states.ChangeChatGPTAboutMe.text)
async def change_profile_info(message: Message, state: FSMContext):

    if len(message.text) > 256:
        return await message.answer("Максимальная длина 256 символов")
    await db.update_chatgpt_about_me(message.from_user.id, message.text)  # Обновляем данные в базе
    await message.answer("Описание обновлено!")
    await state.finish()


# Хендлер для сброса настроек ChatGPT
@dp.callback_query_handler(text="reset_chatgpt_settings", state="*")
async def reset_chatgpt_settings(call: CallbackQuery, state: FSMContext):

    await db.update_chatgpt_settings(call.from_user.id, "")
    await db.update_chatgpt_about_me(call.from_user.id, "")  # Сброс данных
    await call.answer("Данные обновлены", show_alert=True)


# Хендлер для изменения настроек ChatGPT
@dp.callback_query_handler(text="chatgpt_settings", state="*")
async def chatgpt_setting(call: CallbackQuery, state: FSMContext):

    user = await db.get_user(call.from_user.id)
    await call.message.answer(
        '<b>Введите запрос</b>\n\nНастройте ChatGPT как вам удобно - тон, настроение, эмоциональный окрас сообщений ⤵️\n\n<u><a href="https://telegra.ph/Tonkaya-nastrojka-ChatGPT-06-30">Инструкция.</a></u>',
        disable_web_page_preview=True,
        reply_markup=user_kb.get_menu(user["default_ai"]))
    await state.set_state(states.ChangeChatGPTSettings.text)  # Устанавливаем состояние ввода настроек
    await call.answer()


# Хендлер для сохранения новых настроек ChatGPT
@dp.message_handler(state=states.ChangeChatGPTSettings.text)
async def change_profile_settings(message: Message, state: FSMContext):

    if len(message.text) > 256:
        return await message.answer("Максимальная длина 256 символов")
    await db.update_chatgpt_settings(message.from_user.id, message.text)  # Обновляем настройки в базе
    await message.answer("Описание обновлено!")
    await state.finish()


# Основной хендлер для обработки сообщений и генерации запросов
@dp.message_handler()
async def gen_prompt(message: Message, state: FSMContext):

    await state.update_data(prompt=message.text)  # Сохраняем запрос пользователя
    user = await db.get_user(message.from_user.id)
    if user is None:
        await message.answer("Введите команду /start для перезагрузки бота")
        return await message.bot.send_message(796644977, message.from_user.id)

    if user["default_ai"] == "chatgpt":
        if user["tokens"] <= 0 and user["free_chatgpt"] <= 0:
            return await not_enough_balance(message.bot, message.from_user.id, "chatgpt")

        data = await state.get_data()
        system_msg = user["chatgpt_about_me"] + "\n" + user["chatgpt_settings"]
        messages = [{"role": "system", "content": system_msg}] if "messages" not in data else data["messages"]
        update_messages = await get_gpt(prompt=message.text, messages=messages, user_id=message.from_user.id,
                                        bot=message.bot)  # Генерация ответа от ChatGPT
        await state.update_data(messages=update_messages)

    elif user["default_ai"] == "image":
        await get_mj(message.text, message.from_user.id, message.bot)  # Генерация изображения через MidJourney


# Хендлер для обработки фотографий
@dp.message_handler(is_media_group=False, content_types="photo")
async def photo_imagine(message: Message, state: FSMContext):

    if message.caption is None:
        await message.answer("Добавьте описание к фотографии")
        return
    file = await message.photo[-1].get_file()
    photo_url = f"https://api.telegram.org/file/bot{TOKEN}/{file.file_path}"
    ds_photo_url = await more_api.upload_photo_to_host(photo_url)  # Загрузка фото на внешний хостинг
    if ds_photo_url == "error":
        await message.answer("Генерация с фото недоступна, повторите попытку позже")
        await message.bot.send_message(bug_id, "Необходимо заменить API-ключ фотохостинга")
        return
    prompt = ds_photo_url + " " + message.caption  # Создаем запрос на основе фотографии и описания
    await state.update_data(prompt=prompt)
    await get_mj(prompt, message.from_user.id, message.bot)


# Хендлер для обработки альбомов (групповых фото)
@dp.message_handler(is_media_group=True, content_types=ContentType.ANY)
async def handle_albums(message: Message, album: List[Message], state: FSMContext):
    
    if len(album) != 2 or not (album[0].photo and album[1].photo):
        return await message.answer("Пришлите два фото, чтобы их склеить")

    # Обработка первого фото
    file = await album[0].photo[-1].get_file()
    photo_url = f"https://api.telegram.org/file/bot{TOKEN}/{file.file_path}"
    ds_photo_url1 = await more_api.upload_photo_to_host(photo_url)

    # Обработка второго фото
    file = await album[1].photo[-1].get_file()
    photo_url = f"https://api.telegram.org/file/bot{TOKEN}/{file.file_path}"
    ds_photo_url2 = await more_api.upload_photo_to_host(photo_url)

    prompt = f"{ds_photo_url1} {ds_photo_url2}"  # Создаем запрос для двух фото
    await state.update_data(prompt=prompt)
    await get_mj(prompt, message.from_user.id, message.bot)  # Генерация изображения через MidJourney



