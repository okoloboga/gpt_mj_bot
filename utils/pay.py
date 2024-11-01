import hashlib  # Для генерации хешей
import hmac     # Для создания HMAC подписи
import json     # Для работы с JSON
import logging
import random   # Для генерации случайных чисел
from datetime import datetime, timedelta  # Для работы с датами
from urllib.parse import urlencode  # Для кодирования URL параметров

import requests  # Для выполнения HTTP-запросов

import config  # Импорт конфигурации
from config import FreeKassa, LAVA_API_KEY, LAVA_SHOP_ID, PayOK, Tinkoff  # Импорт настроек платежных систем
from utils import db  # Импорт функций работы с базой данных


logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(filename)s:%(lineno)d #%(levelname)-8s '
           '[%(asctime)s] - %(name)s - %(message)s')


# Функция для получения ссылки оплаты через Tinkoff
def get_pay_url_tinkoff(order_id, amount):

    # Формирование данных для запроса на оплату через Tinkoff
    data = {
        "TerminalKey": Tinkoff.terminal_id,
        "Amount": amount * 100,  # Сумма в копейках
        "OrderId": order_id,  # Идентификатор заказа
        "NotificationURL": "http://91.192.102.250/api/pay/tinkoff"  # URL для уведомлений о статусе оплаты
    }
    # Строка для подписи
    sing_str = f"{amount * 100}http://91.192.102.250/api/pay/tinkoff{order_id}{Tinkoff.api_token}{Tinkoff.terminal_id}"
    # Генерация подписи (SHA256)
    sign = hashlib.sha256(sing_str.encode('utf-8')).hexdigest()

    data["Token"] = sign  # Добавляем подпись в запрос

    # Отправка запроса на инициализацию оплаты
    res = requests.post("https://securepay.tinkoff.ru/v2/Init", json=data)
    logger.info(f'Tinkoff Response: {res.json()}')
    res_data = res.json()  # Получение ответа в формате JSON
    return res_data["PaymentURL"]  # Возвращаем URL для оплаты


# Функция для получения ссылки оплаты через PayOK
def get_pay_url_payok(order_id, amount):

    desc = "Пополнение баланса NeuronAgent"  # Описание платежа
    currency = "RUB"  # Валюта
    # Формирование строки для подписи
    sign_string = '|'.join(
        str(item) for item in
        [amount, order_id, PayOK.shop_id, currency, desc, PayOK.secret]
    )
    # Генерация подписи (MD5)
    sign = hashlib.md5(sign_string.encode())

    # Параметры для оплаты
    params = {"amount": amount, "payment": order_id, "shop": PayOK.shop_id, "desc": desc, "currency": currency,
              "sign": sign.hexdigest()}

    # Возвращаем URL для оплаты через PayOK
    return "https://payok.io/pay?" + urlencode(params)


# Функция для получения ссылки оплаты через FreeKassa
def get_pay_url_freekassa(order_id, amount):

    md5 = hashlib.md5()  # Инициализация MD5 хеша
    # Формируем строку для подписи
    md5.update(
        f'{FreeKassa.shop_id}:{amount}:{FreeKassa.secret1}:RUB:{order_id}'.encode('utf-8'))
    pwd = md5.hexdigest()  # Генерация подписи
    # Формируем URL для оплаты через FreeKassa
    pay_url = f"https://pay.freekassa.com/?m={FreeKassa.shop_id}&oa={amount}&currency=RUB&o={order_id}&s={pwd}"
    return pay_url


# Вспомогательная функция для сортировки словаря
def sortDict(data: dict):

    sorted_tuple = sorted(data.items(), key=lambda x: x[0])  # Сортировка по ключам
    return dict(sorted_tuple)


# Функция для получения ссылки оплаты через Lava
def get_pay_url_lava(user_id, amount):

    # Формирование данных для платежа
    payload = {
        "sum": amount,
        "orderId": str(user_id) + ":" + str(random.randint(10000, 1000000)),  # Уникальный идентификатор заказа
        "shopId": LAVA_SHOP_ID
    }

    # Сортировка данных
    payload = sortDict(payload)
    jsonStr = json.dumps(payload).encode()

    # Генерация подписи (HMAC-SHA256)
    sign = hmac.new(bytes(LAVA_API_KEY, 'UTF-8'), jsonStr, hashlib.sha256).hexdigest()
    headers = {"Signature": sign, "Accept": "application/json", "Content-Type": "application/json"}
    
    # Отправляем запрос на создание счета
    res = requests.post("https://api.lava.ru/business/invoice/create", json=payload, headers=headers)
    return res.json()["data"]["url"]  # Возвращаем URL для оплаты


# Функция для обработки успешной оплаты токенов/запросов
async def process_purchase(bot, order_id):
    
    # Получаем информацию о заказе
    order = await db.get_order(order_id)

    # Проверяем, была ли оплата уже обработана
    if order["pay_time"]:
        return

    # Обновляем время оплаты
    await db.set_order_pay(order_id)

    user_id = order["user_id"]  # Получаем ID пользователя
    user = await db.get_user(user_id)  # Получаем информацию о пользователе

    # Обновляем токены или запросы в зависимости от типа заказа
    if order["order_type"] == "chatgpt":
        new_tokens = user["tokens"] + order["quantity"]
        await db.update_tokens(user_id, new_tokens)
        await bot.send_message(user_id, f"💰 Вы успешно приобрели {order['quantity']} токенов для ChatGPT.")
    elif order["order_type"] == "midjourney":
        new_requests = user["mj"] + order["quantity"]
        await db.update_requests(user_id, new_requests)
        await bot.send_message(user_id, f"💰 Вы успешно приобрели {order['quantity']} запросов для MidJourney.")


""" Старая функция обработки оплаты подписки

# Функция для обработки успешной оплаты подписки
async def process_sub(bot, order_id):
    # Получаем информацию о заказе подписки из базы данных
    sub_order = await db.get_sub_order(order_id)
    # Если подписка уже была оплачена, выходим
    if sub_order["pay_time"]:
        return
    # Обновляем статус оплаты в базе данных
    await db.set_sub_order_pay(order_id)
    
    user_id = sub_order["user_id"]  # Получаем ID пользователя
    user = await db.get_user(user_id)  # Получаем информацию о пользователе

    # Вычисляем новое время окончания подписки
    if user["sub_time"] < datetime.now():
        base_sub_time = datetime.now()
    else:
        base_sub_time = user["sub_time"]
    sub_time = base_sub_time + timedelta(days=sub_order["days"])  # Добавляем количество дней подписки

    sub_type = sub_order["sub_type"]  # Получаем тип подписки
    tokens = config.sub_types[sub_type]["tokens"]  # Количество токенов для данной подписки
    mj = config.sub_types[sub_type]["mj"]  # Количество запросов MidJourney для данной подписки
    
    # Обновляем информацию о подписке в базе данных
    await db.update_sub_info(user_id, sub_time, sub_type, tokens, mj)
    
    # Отправляем сообщение пользователю о успешной покупке подписки
    await bot.send_message(user_id, f"💰 Вы успешно приобрели подписку.")

"""