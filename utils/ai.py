import random

import aiohttp  # Для асинхронных HTTP-запросов
import openai  # Работа с API OpenAI
import requests  # Для синхронных HTTP-запросов
from aiogram import Bot  # Для работы с ботом
from midjourney_api import TNL  # Импорт библиотеки для взаимодействия с MidJourney
from googletranslatepy import Translator  # Библиотека для перевода текста

from config import OPENAPI_TOKEN, midjourney_webhook_url, MJ_API_KEY, TNL_API_KEY, TOKEN, NOTIFY_URL, TNL_API_KEY1, \
    go_api_token  # Импорт конфигураций и токенов
from utils import db  # Работа с базой данных

# Устанавливаем API-ключ для OpenAI
openai.api_key = OPENAPI_TOKEN
openai.log = "error"  # Устанавливаем уровень логирования

# Базовый URL для работы с MidJourney
mj_base_url = "https://api.justimagineapi.org/v1"

# Заголовки для API GoAPI (используется для взаимодействия с MidJourney)
go_api_headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'X-API-KEY': go_api_token  # Токен для доступа к GoAPI
}


# Класс для работы с GoAPI (MidJourney)
class GoAPI:

    # Общая функция для создания запроса к GoAPI
    @staticmethod
    async def create_request(data, action, request_id):

        data["webhook_endpoint"] = midjourney_webhook_url + "/" + str(request_id)  # Указываем вебхук для ответа
        data["notify_progress"] = True  # Включаем уведомления о прогрессе
        async with aiohttp.ClientSession() as session:
            async with session.post(
                    url=f"https://api.goapi.ai/mj/v2/{action}",  # URL для API
                    json=data,
                    headers=go_api_headers  # Заголовки
            ) as response:
                response_content = await response.json()  # Получаем ответ в формате JSON
                print(response_content)
                return response_content


    # Функция для генерации изображения на основе запроса (prompt)
    @staticmethod
    async def imagine(prompt, request_id):

        data = {
            "process_mode": "fast",  # Ускоренный режим
            "prompt": prompt,  # Текстовый запрос
        }
        return await GoAPI.create_request(data, "imagine", request_id)


    # Функция для улучшения изображения (upscale)
    @staticmethod
    async def upscale(task_id, index, action_id):

        data = {
            "origin_task_id": task_id,  # Идентификатор задачи
            "index": index  # Индекс изображения для улучшения
        }
        return await GoAPI.create_request(data, "upscale", action_id)


    # Функция для вариации изображения
    @staticmethod
    async def variation(task_id, index, request_id):

        data = {
            "origin_task_id": task_id,  # Идентификатор задачи
            "index": index  # Индекс изображения для вариации
        }
        return await GoAPI.create_request(data, "variation", request_id)


    # Функция для увеличения масштаба изображения (outpaint)
    @staticmethod
    async def outpaint(task_id, zoom_ratio, request_id):

        data = {
            "origin_task_id": task_id,  # Идентификатор задачи
            "zoom_ratio": zoom_ratio  # Коэффициент увеличения
        }
        return await GoAPI.create_request(data, "outpaint", request_id)


# Функция для получения MidJourney токена в зависимости от индекса
def get_mj_token(index):

    if index == 0:
        return TNL_API_KEY
    elif index == 1:
        return TNL_API_KEY1


# Добавление действия пользователя в базу данных (например, создание изображения или запрос в AI)
async def add_mj_action(user_id, action_type):

    action_id = await db.add_action(user_id, action_type)  # Сохраняем действие в базе
    try:
        requests.post(NOTIFY_URL + f"/action/{action_id}")  # Отправляем уведомление о новом действии
    except:
        pass
    return action_id


# Функция для отправки сообщения об ошибке админу бота
async def send_error(text):

    my_bot = Bot(TOKEN)
    await my_bot.send_message(796644977, text)


# Функция для перевода текста на английский язык
async def get_translate(text):

    translator = Translator(target="en")  # Переводим на английский
    translate = translator.translate(text)
    return translate


# Функция для отправки запроса в ChatGPT
async def get_gpt(messages):

    status = True
    tokens = 0
    try:
        response = await openai.ChatCompletion.acreate(model="gpt-4o-mini",  # Модель GPT-4
                                                       messages=messages[-10:])  # Последние 10 сообщений
    except (openai.error.ServiceUnavailableError, openai.error.APIError):
        status = False
        content = "Генерация текста временно недоступна, повторите запрос позднее"  # Сообщение об ошибке
    if status:
        content = response["choices"][0]["message"]["content"]  # Получаем ответ
        tokens = response["usage"]["total_tokens"]  # Получаем количество использованных токенов
    return {"status": status, "content": content, "tokens": tokens}  # Возвращаем результат


# Функция для отправки запроса в MidJourney через GoAPI
async def get_mdjrny(prompt, user_id):

    translated_prompt = await get_translate(prompt)  # Переводим запрос на английский
    action_id = await db.add_action(user_id, "image", "imagine")  # Сохраняем действие в базе данных
    response = await GoAPI.imagine(translated_prompt, action_id)  # Отправляем запрос в GoAPI
    return response
    
    # acc_id = random.randint(0, 1)
    # api_key = get_mj_token(acc_id)
    # api_key_number = acc_id
    # try:
    #     payload = {
    #         "msg": translated_prompt,
    #         "ref": str(action_id),
    #         "webhookOverride": midjourney_webhook_url
    #     }
    #
    #     headers = {
    #         'Content-Type': 'application/json',
    #         'Authorization': f'Bearer {api_key}'
    #     }
    #     res = requests.post(mj_base_url + "/imagine", json=payload, headers=headers)
    #     print(res.content)
    #     res = res.json()
    #     print(res)
    # except ValueError as e:
    #     print("1111")
    #     print("ASLKDALKSD")
    #     # res = await reserve_mj(translated_prompt, user_id)
    #     # mj_api = "reserve"
    #     status = False
    #
    # error = None
    # task_id = None

    return {"status": status,
            # "mj_api": mj_api,
            "error": error, "task_id": task_id}


# Функция для выбора и улучшения изображения в MidJourney
async def get_choose_mdjrny(task_id, image_id, user_id):

    action_id = await db.add_action(user_id, "image", "upscale")  # Сохраняем действие в базе данных
    response = await GoAPI.upscale(task_id, image_id, action_id)  # Отправляем запрос на улучшение изображения
    return response
    # try:
    #     payload = {
    #         "button": f"U{image_id}",
    #         "buttonMessageId": buttonMessageId,
    #         "ref": str(action_id),
    #         "webhookOverride": midjourney_webhook_url + "/choose"
    #     }
    #     headers = {
    #         'Content-Type': 'application/json',
    #         'Authorization': f'Bearer {api_key}'
    #     }
    #     res = requests.post(mj_base_url + "/button", json=payload, headers=headers)
    #     res = res.json()
    #     print(res)
    #     return {"status": True}
    # except requests.exceptions.JSONDecodeError:
    #     return {"status": False}


# Функция для нажатия кнопок MidJourney (вариации или улучшения)
async def press_mj_button(button, buttonMessageId, user_id, api_key_number):
    
    action_id = await db.add_action(user_id, "image", "imagine")  # Сохраняем действие в базе данных
    status = True
    api_key = get_mj_token(api_key_number)  # Получаем токен
    try:
        payload = {
            "button": button,
            "buttonMessageId": buttonMessageId,
            "ref": str(action_id),
            "webhookOverride": midjourney_webhook_url + "/button"
        }
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        res = requests.post(mj_base_url + "/button", json=payload, headers=headers)  # Отправляем запрос
        res = res.json()
    except requests.exceptions.JSONDecodeError:
        status = False  # Ошибка при обработке JSON
    return status
