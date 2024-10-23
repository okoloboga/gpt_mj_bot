import asyncio
from datetime import datetime, timedelta
from typing import Annotated

import config
import utils
from config import NOTIFY_URL, bug_id
from keyboards import user as user_kb
from fastapi import FastAPI, Request, HTTPException, Form  # Импорт необходимых классов для работы с FastAPI
from pydantic import BaseModel  # Импорт базовой модели данных
from create_bot import bot  # Импорт бота
from io import BytesIO  # Для работы с потоками байтов
from utils import db  # Импорт функций работы с базой данных
import requests  # Для синхронных HTTP-запросов
import uvicorn  # Для запуска сервера FastAPI


# Инициализация FastAPI приложения
app = FastAPI()


# Класс для обработки вебхуков от системы платежей Lava
class LavaWebhook(BaseModel):

    order_id: str  # Идентификатор заказа
    status: str  # Статус платежа
    amount: float  # Сумма платежа


# Класс для обработки вебхуков от системы PayOK
class PayOKWebhook(BaseModel):

    payment_id: str  # Идентификатор платежа
    amount: float  # Сумма платежа


# Функция для отправки фотографии, сгенерированной MidJourney
async def send_mj_photo(user_id, photo_url, kb):

    try:
        response = requests.get(photo_url, timeout=5)  # Загружаем изображение по URL
    except requests.exceptions.Timeout:
        img = photo_url  # В случае таймаута просто используем URL как картинку
    except requests.exceptions.ConnectionError:
        img = photo_url  # В случае ошибки соединения также используем URL
    else:
        img = BytesIO(response.content)  # Преобразуем изображение в байтовый поток
    await bot.send_photo(user_id, photo=img, reply_markup=kb)  # Отправляем изображение пользователю


# Функция для пополнения баланса пользователя
async def add_balance(user_id, amount):

    print(user_id)
    user = await db.get_user(user_id)  # Получаем информацию о пользователе
    print("USER", user)
    if user is None:
        return
    stock = 0  # Стартовый бонус
    
    # Если это первый платеж или прошло менее суток с момента последнего бонуса
    if not user["is_pay"] and int(datetime.now().timestamp()) - user["new_stock_time"] < 86400:
        stock = int(amount * 0.3)  # Добавляем 30% бонус
        await db.update_new_stock_time(user_id, 0)
    elif int(datetime.now().timestamp()) - user["stock_time"] < 86400:
        stock = int(amount * 0.1)  # Добавляем 10% бонус
        await db.update_stock_time(user_id, 0)
    requests.delete(NOTIFY_URL + f"/stock/{user_id}")  # Удаляем уведомление о бонусе
    await db.update_is_pay(user_id, True)  # Обновляем статус оплаты
    await db.add_balance(user_id, amount + stock)  # Добавляем баланс пользователю
    await db.add_order(user_id, amount, stock)  # Добавляем запись о пополнении
    print("???") # ???
    await bot.send_message(user_id, f"💰 Успешное пополнение ({amount + stock} руб.)")  # Сообщаем пользователю


# Функция для обработки платежей
async def process_pay(order_id, amount):

    if order_id.startswith("s"):  # Если это подписка
        await utils.pay.process_purchase(bot, int(order_id)) # Обрабатываем покупку токенов или запросов
        # await utils.pay.process_sub(bot, int(order_id[1:]))  # Обрабатываем подписку
    else:
        user_id = int(order_id.split("_")[0])  # Если это пополнение баланса
        await add_balance(user_id, amount)  # Пополняем баланс


# Обработка платежей от FreeKassa
@app.get('/api/pay/freekassa')
async def check_pay_freekassa(MERCHANT_ORDER_ID, AMOUNT):

    await process_pay(MERCHANT_ORDER_ID, int(AMOUNT))  # Обрабатываем платеж
    return 'YES'


# Обработка платежей от Lava
@app.post('/api/pay/lava')
async def check_pay_freekassa(data: LavaWebhook):

    if data.status != "success":
        raise HTTPException(200)  # Если статус не успешный, возвращаем HTTP 200
    await process_pay(data.order_id, int(data.amount))  # Обрабатываем платеж
    raise HTTPException(200)


# Обработка платежей от Tinkoff
@app.post('/api/pay/tinkoff')
async def check_pay_tinkoff(request: Request):

    data = await request.json()  # Получаем данные из запроса
    if data["Status"] != "CONFIRMED":  # Если статус не подтвержден, игнорируем
        return "OK"

    await process_pay(data["OrderId"], int(data["Amount"] / 100))  # Обрабатываем платеж
    return "OK"


# Обработка платежей от PayOK
@app.post('/api/pay/payok')
async def check_pay_freekassa(payment_id: Annotated[str, Form()], amount: Annotated[str, Form()]):

    await process_pay(payment_id, int(amount))  # Обрабатываем платеж
    raise HTTPException(200)


# Обработка webhook от MidJourney
@app.post('/api/midjourney/{action_id}')
async def get_midjourney(action_id: int, request: Request):
    
    action = await db.get_action(action_id)  # Получаем информацию о действии
    data = await request.json()  # Получаем данные из запроса
    user_id = action["user_id"]  # Идентификатор пользователя
    user = await db.get_user(user_id)  # Получаем данные о пользователе
    image_url = data["task_result"]["image_url"]  # URL сгенерированного изображения

    image_path = f'photos/{action_id}.png'  # Путь для сохранения изображения
    res = requests.get(image_url)  # Загружаем изображение
    with open(image_path, "wb") as f:
        f.write(res.content)  # Сохраняем изображение

    # В зависимости от типа изображения отправляем пользователю разные кнопки
    if action["image_type"] in ("imagine", "vary", "zoom"):
        await bot.send_photo(user_id, open(image_path, "rb"),
                             reply_markup=user_kb.get_try_prompt_or_choose(data["task_id"],
                                                                           include_try=True))
        if user["free_image"] > 0:
            await db.remove_free_image(user["user_id"])  # Уменьшаем количество бесплатных изображений
        else:
            await db.remove_image(user["user_id"])  # Уменьшаем количество доступных изображений
    elif action["image_type"] == "upscale":
        await bot.send_photo(user_id, open(image_path, "rb"),
                             reply_markup=user_kb.get_choose(data["task_id"]))
    return 200
