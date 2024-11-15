import random
import logging

import aiohttp  # Для асинхронных HTTP-запросов
import openai  # Работа с API OpenAI
import requests  # Для синхронных HTTP-запросов
from aiogram import Bot  # Для работы с ботом
from midjourney_api import TNL  # Импорт библиотеки для взаимодействия с MidJourney
from googletranslatepy import Translator  # Библиотека для перевода текста
# from gtts import gTTS  # Библиотека для синтеза речи

# import speech_recognition as sr  # Библиотека для распознавания речи
# from pydub import AudioSegment  # Библиотека для работы с аудио
import tempfile
import os

from config import OPENAPI_TOKEN, midjourney_webhook_url, MJ_API_KEY, TNL_API_KEY, TOKEN, NOTIFY_URL, TNL_API_KEY1  # Импорт конфигураций и токенов
from utils import db  # Работа с базой данных
from utils.mj_apis import GoAPI, ApiFrame, MidJourneyAPI


logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(filename)s:%(lineno)d #%(levelname)-8s '
           '[%(asctime)s] - %(name)s - %(message)s')


# Устанавливаем API-ключ для OpenAI
openai.api_key = OPENAPI_TOKEN
openai.log = "error"  # Устанавливаем уровень логирования

# Инициализация MidJourneyAPI
mj_api = MidJourneyAPI(primary_api="goapi")  # Начнем с GoAPI

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


# Функция для отправки запроса в MidJourney
async def get_mdjrny(prompt, user_id):

    translated_prompt = await get_translate(prompt)  # Переводим запрос на английский
    request_id = await db.add_action(user_id, "image", "imagine")  # Сохраняем действие в базе данных
    response = await mj_api.imagine(translated_prompt, request_id)  # Отправляем запрос в Midjourney
    
    logger.info(f'Request ID: {request_id}, response: {response}')

    return response


# Функция для выбора и улучшения изображения в MidJourney
async def get_choose_mdjrny(task_id, image_id, user_id):

    action_id = await db.add_action(user_id, "image", "upscale")  # Сохраняем действие в базе данных

    logger.info(f'Task ID: {task_id}, Image ID: {image_id}, Action ID: {action_id}')

    response = await mj_api.upscale(task_id, image_id, action_id)  # Отправляем запрос на улучшение изображения
    return response


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
        res = requests.post("https://api.justimagineapi.org/v1" + "/button", json=payload, headers=headers)  # Отправляем запрос
        res = res.json()
    except requests.exceptions.JSONDecodeError:
        status = False  # Ошибка при обработке JSON
    return status


# """Работа с голосовыми сообщениями"""
# # Функция для преобразования голосового сообщения в текст
# def voice_to_text(file_path):
#     recognizer = sr.Recognizer()
#     audio = AudioSegment.from_file(file_path)
    
#     # Сохраняем аудио как временный wav-файл
#     with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_wav_file:
#         audio.export(temp_wav_file.name, format="wav")
#         temp_wav_file_path = temp_wav_file.name

#     with sr.AudioFile(temp_wav_file_path) as source:
#         audio_data = recognizer.record(source)
        
#     os.remove(temp_wav_file_path)  # Удаляем временный файл
    
#     try:
#         text = recognizer.recognize_google(audio_data, language="ru-RU")
#         return text
#     except sr.UnknownValueError:
#         return "Не удалось распознать речь"
#     except sr.RequestError:
#         return "Ошибка запроса к сервису распознавания"

    
# # Функция для преобразования текста в аудио
# def text_to_speech(text):
#     tts = gTTS(text=text, lang='ru')

#     # Сохраняем результат как временный mp3-файл
#     with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio_file:
#         temp_audio_path = temp_audio_file.name
#         tts.save(temp_audio_path)
        
#     audio_file = InputFile(temp_audio_path)
#     os.remove(temp_audio_path)  # Удаляем временный файл после использования
#     return audio_file
