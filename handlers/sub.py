from datetime import datetime, timedelta

from aiogram.dispatcher.filters import Text
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery

import config
import keyboards.user as user_kb  # Клавиатуры для взаимодействия с пользователями (выбор подписки, оплата)
import utils
from create_bot import dp  # Диспетчер для регистрации хендлеров
from utils import db, pay  # Модули для работы с базой данных и платежными сервисами

vary_types = {"subtle": "Subtle", "strong": "Strong"}  # Типы вариаций для MidJourney


# Функция для получения ссылок на оплату для разных сервисов
def get_pay_urls(order_id, amount):
    return {
        "tinkoff": pay.get_pay_url_tinkoff(order_id, amount),  # Ссылка для оплаты через Tinkoff
        "freekassa": pay.get_pay_url_freekassa(order_id, amount),  # Ссылка для оплаты через FreeKassa
        "payok": pay.get_pay_url_payok(order_id, amount),  # Ссылка для оплаты через PayOK
    }


'''Новые функции выбора покупки токенов - GPT или MJ'''

# Меню для выбора между ChatGPT и MidJourney
@dp.callback_query_handler(text="buy_sub")
async def choose_neural_network(call: CallbackQuery):

    await call.message.edit_text("""
Выберите нейросеть⤵️""", 
    reply_markup=user_kb.get_neural_network_menu())


# Меню для выбора количества токенов ChatGPT
@dp.callback_query_handler(text="buy_chatgpt_tokens")
async def choose_chatgpt_tokens(call: CallbackQuery):

    user_id = call.from_user.id
    
    # Получаем данные о последнем уведомлении пользователя
    user_data = await db.get_user_notified_gpt(user_id)
    now = datetime.now()

    # Проверяем, было ли уведомление отправлено менее 24 часов назад
    if user_data and user_data['last_notification']:
        last_notification = user_data['last_notification']
        
        # Если уведомление было менее 24 часов назад, показываем меню со скидкой
        if now < last_notification + timedelta(hours=24):
            await call.message.edit_text(
                "Выберите количество токенов со скидкой⤵️",
                reply_markup=user_kb.get_chatgpt_discount_tokens_menu()
            )
            return
    
    # Если уведомление не было отправлено или прошло больше 24 часов, показываем обычное меню
    await call.message.edit_text(
        "Выберите количество токенов⤵️",
        reply_markup=user_kb.get_chatgpt_tokens_menu()
    )


# Меню для выбора количества запросов MidJourney
@dp.callback_query_handler(text="buy_midjourney_requests")
async def choose_midjourney_requests(call: CallbackQuery):
    user_id = call.from_user.id
    
    # Получаем данные о последнем уведомлении пользователя
    user_data = await db.get_user_notified_mj(user_id)
    now = datetime.now()

    # Проверяем, было ли уведомление отправлено менее 24 часов назад
    if user_data and user_data['last_notification']:
        last_notification = user_data['last_notification']
        
        # Если уведомление было менее 24 часов назад, показываем меню со скидкой
        if now < last_notification + timedelta(hours=24):
            await call.message.edit_text(
                "Выберите количество запросов со скидкой⤵️",
                reply_markup=user_kb.get_midjourney_discount_requests_menu()
            )
            return
    
    await call.message.edit_text("""
Выберите количество запросов⤵️""",
    reply_markup=user_kb.get_midjourney_requests_menu())


# Реагирование на нажатие кнопки с выбором количества тоенов для GPT
@dp.callback_query_handler(Text(startswith="select_chatgpt_tokens:"))
async def handle_chatgpt_tokens_purchase(call: CallbackQuery):

    user_id = call.from_user.id

    tokens = int(call.data.split(":")[1])  # Получаем количество токенов
    amount = int(call.data.split(":")[2])  # Получаем цену за количество токенов
    discounts = [139, 224, 381]
    user_discount = await db.get_user_notified_gpt(user_id)

    if user_discount is None or (user_discount['used'] != True or (user_discount['used'] == True and amount not in discounts)):
        
        if amount in discounts:  # Покупка со скидкой
            await db.update_used_discount_gpt(user_id)

        # Создаем заказ для покупки токенов в базе данных
        order_id = await db.add_order(call.from_user.id, amount, "chatgpt", tokens)

        # Генерируем ссылки для оплаты
        urls = get_pay_urls('s'+str(order_id), amount)
    
        # Отправляем пользователю сообщение с выбором способа оплаты
        await call.message.edit_text(f"Вы выбрали {tokens} токенов для 💬ChatGPT, стоимость {amount}₽.",
                                     reply_markup=user_kb.get_pay_urls(urls, order_id))
    
    else:
        await call.message.edit_text("Вы уже использовали скидку")

# Реагирование на нажатие кнопки с выбором количества запросов для Midjourney
@dp.callback_query_handler(Text(startswith="select_midjourney_requests:"))
async def handle_midjourney_requests_purchase(call: CallbackQuery):

    user_id = call.from_user.id
    requests_count = int(call.data.split(":")[1])  # Получаем количество запросов
    amount = int(call.data.split(":")[2])  # Получаем цену за количество запросов
    discounts = [246, 550, 989]
    user_discount = await db.get_user_notified_mj(user_id)

    if user_discount is None or (user_discount['used'] != True or (user_discount['used'] == True and amount not in discounts)):
        
        if amount in discounts:  # Покупка со скидкой
            await db.update_used_discount_mj(user_id)
        
        # Создаем заказ для покупки запросов в базе данных
        order_id = await db.add_order(call.from_user.id, amount, "midjourney", requests_count)

        # Генерируем ссылки для оплаты
        urls = get_pay_urls('s'+str(order_id), amount)

        # Отправляем пользователю сообщение с выбором способа оплаты
        await call.message.edit_text(f"Вы выбрали {requests_count} запросов для 🎨MidJourney, стоимость {amount}₽.",
                                     reply_markup=user_kb.get_pay_urls(urls, order_id))
    else:
        await call.message.edit_text("Вы уже использовали скидку")

''' Старые функции подписок 

# Хендлер для выбора подписки через callback
@dp.callback_query_handler(text="buy_sub")
async def choose_amount(call: CallbackQuery):
    # Отправляем сообщение с описанием различных тарифов и клавиатурой для выбора
    await call.message.edit_text("""
Выберите тариф⤵️

Тариф <b>«Базовый»</b>
1 млн токенов для ChatGPT
10 запросов в Midjourney в день

Тариф <b>«Стандарт»</b>
2 млн токенов для ChatGPT
20 запросов в Midjourney в день

Тариф <b>«Премиум»</b>
5 млн токенов для ChatGPT
40 запросов в Midjourney в день

Тариф <b>«Иллюстратор»</b>
50 тыс токенов для ChatGPT
100 запросов в Midjourney в день

Тариф <b>«Автор»</b>
10 млн токенов для ChatGPT
5 запросов в Midjourney в день""", reply_markup=user_kb.sub_types)


# Хендлер для выбора типа подписки через callback
@dp.callback_query_handler(Text(startswith="sub_type:"))
async def choose_amount(call: CallbackQuery):
    sub_type = call.data.split(":")[1]  # Получаем тип подписки из callback-запроса
    discount = False  # Проверка, есть ли скидка
    try:
        call.data.split(":")[2]  # Проверяем, есть ли третий элемент в запросе (если есть, значит это скидка)
        discount = True
    except IndexError:
        pass

    # В зависимости от наличия скидки выбираем цены
    if discount:
        prices = config.sub_types[sub_type]["discount_prices"]
    else:
        prices = config.sub_types[sub_type]["prices"]

    # Предлагаем выбрать период подписки
    await call.message.edit_text("Выберите период подписки⤵️",
                                 reply_markup=user_kb.get_sub_period(sub_type, prices, discount))


# Хендлер для выбора периода подписки
@dp.callback_query_handler(Text(startswith="sub_period:"))
async def choose_amount(call: CallbackQuery):
    sub_type = call.data.split(":")[1]  # Тип подписки
    sub_period_id = int(call.data.split(":")[2])  # Период подписки
    discount = False
    try:
        call.data.split(":")[3]  # Проверяем наличие скидки
        discount = True
    except IndexError:
        pass

    # Если используется скидка, проверяем, был ли она уже использована
    if discount:
        order = await db.check_discount_order(call.from_user.id)
        if order:
            await call.answer("Вы уже использовали скидку", show_alert=True)
            return await call.message.delete()

        # Если скидка доступна, берем данные о цене со скидкой
        price_data = config.sub_types[sub_type]["discount_prices"][sub_period_id]
    else:
        # Если скидки нет, берем обычные цены
        price_data = config.sub_types[sub_type]["prices"][sub_period_id]

    amount = price_data["price"]  # Цена подписки
    # Создаем заказ на подписку в базе данных
    order_id = await db.add_sub_order(call.from_user.id, amount, sub_type, discount, price_data["days"])
    # Генерируем ссылки для оплаты
    urls = get_pay_urls("s" + str(order_id), amount)
    # Отправляем сообщение с предложением оплатить подписку
    await call.message.answer(f"""💰 Сумма: {amount} рублей

♻️ Средства зачислятся автоматически""", reply_markup=user_kb.get_pay_urls(urls, order_id))
    await call.answer()
'''

# Хендлер для оплаты через Telegram (проплаченный функционал)
@dp.callback_query_handler(Text(startswith="tg_stars:"))
async def back_to_buy_vpn(call: CallbackQuery):

    order_id = int(call.data.split(":")[1])  # Получаем ID заказа
    order = await db.get_order(order_id)  # Получаем данные о заказе из базы данных

    # Отправляем пользователю инвойс для оплаты через Telegram
    await call.bot.send_invoice(call.from_user.id,
                                title="Приобретение подписки",
                                description=f"""💰 Сумма: {order['amount']} рублей

♻️ Средства зачислятся автоматически""",
                                provider_token="",  # Токен для оплаты (платежный провайдер)
                                payload=f"{order_id}",  # ID заказа
                                currency="XTR",  # Валюта оплаты
                                prices=[LabeledPrice(label="Подписка", amount=order["amount"] // 2)],  # Цена подписки
                                reply_markup=user_kb.get_tg_stars_pay()  # Кнопка оплаты
                                )
    await call.answer()


# Хендлер для подтверждения оплаты через Telegram
@dp.pre_checkout_query_handler()
async def approve_order(pre_checkout_query: PreCheckoutQuery):

    # Подтверждаем заказ (оплата успешна)
    await pre_checkout_query.bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


# Хендлер для обработки успешной оплаты
@dp.message_handler(content_types="successful_payment")
async def process_successful_payment(message: Message):
    
    order_id = int(message.successful_payment.invoice_payload)  # Получаем ID заказа из payload
    await utils.pay.process_purchase(message.bot, order_id)  # Обрабатываем подписку (обновляем в базе)
