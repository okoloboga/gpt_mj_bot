from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, \
    ReplyKeyboardRemove, WebAppInfo  # Импортируем необходимые классы для создания клавиатур
from urllib import parse  # Модуль для работы с URL


# Клавиатура для вывода реферальных средств (выбор способа вывода)
withdraw_ref_menu = InlineKeyboardMarkup(row_width=2).add(
    InlineKeyboardButton("На банковскую карту", callback_data='withdraw_ref:bank_card')).add(
    InlineKeyboardButton("QIWI", callback_data="withdraw_ref:qiwi"),
    InlineKeyboardButton("На баланс", callback_data="withdraw_ref:balance")
)


# Клавиатура с ссылками для информации о проекте и поддержке
about = InlineKeyboardMarkup(row_width=2).add(InlineKeyboardButton("📢Канал проекта", url="https://t.me/NeuronAgent"),
                                              InlineKeyboardButton("🆘Помощь", url="https://t.me/NeuronSupportBot"),
                                              InlineKeyboardButton("Инструкция для Midjourney", url="https://telegra.ph/Kak-polzovatsya-MidJourney-podrobnaya-instrukciya-10-16"))


# Кнопка для отмены действия (например, при вводе данных)
cancel = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1).add(KeyboardButton("Отмена"))


# Клавиатура для пополнения баланса (предлагает выбрать тариф)
top_up_balance = InlineKeyboardMarkup(row_width=1).add(
    InlineKeyboardButton("💰Выбрать тариф", callback_data="buy_sub"))


# Кнопка для подтверждения подписки на канал и проверки подписки
partner = InlineKeyboardMarkup(row_width=1).add(
    InlineKeyboardButton("↗️Перейти и подписаться", url="https://t.me/NeuronAgent"),
    InlineKeyboardButton("✅Я подписался", callback_data="check_sub"))


# Кнопка для возврата к выбору суммы пополнения
back_to_choose = InlineKeyboardMarkup(row_width=1).add(
    InlineKeyboardButton("🔙Назад", callback_data="back_to_choose_balance"))


# Языковые настройки для клавиатур
lang_text = {"en": "ENG", "ru": "RUS"}


# Кнопка для завершения текущего диалога (например, с ChatGPT) и перевода текста в аудио
def get_clear_or_audio():    
    
    clear_and_audio = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("Завершить диалог", callback_data="clear_content"),
        #InlineKeyboardButton("Озвучить текст", callback_data=f"text_to_audio")
        )


# Клавиатура для настройки ChatGPT
def get_chat_gpt_keyboard(lang, from_msg):

    return InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("Рассказать о себе", callback_data="chatgpt_about_me"),
        InlineKeyboardButton("Настроить ChatGPT", callback_data="chatgpt_settings")
    )


# Клавиатура с настройками аккаунта пользователя (выбор тарифа, смена языка, сброс настроек)
def get_account(lang, from_msg):

    return InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("💰Выбрать тариф", callback_data="buy_sub"),
        InlineKeyboardButton(f"Ответы ChatGPT: {lang_text[lang]}", callback_data=f"change_lang:{lang}:{from_msg}"),
        InlineKeyboardButton("Сбросить настройки ChatGPT", callback_data="reset_chatgpt_settings"),
        InlineKeyboardButton("Инструкция для Midjourney", url="https://telegra.ph/Kak-polzovatsya-MidJourney-podrobnaya-instrukciya-10-16")
    )


# Кнопка для вариации запроса (например, в MidJourney)
def get_try_prompt(ai_type):

    return InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("🔄 Другой вариант", callback_data=f"try_prompt:{ai_type}"))


# Главное меню бота, где пользователь выбирает, с каким AI он хочет работать (ChatGPT или MidJourney)
def get_menu(default_ai):

    if default_ai == "chatgpt":
        return ReplyKeyboardMarkup(resize_keyboard=True, row_width=2).add(KeyboardButton("💬ChatGPT✅"),
                                                                          KeyboardButton("🎨Midjourney"),
                                                                          KeyboardButton("⚙Аккаунт"),
                                                                          KeyboardButton("👨🏻‍💻Поддержка"),
                                                                          KeyboardButton("🤝Партнерская программа"))
    elif default_ai == "image":
        return ReplyKeyboardMarkup(resize_keyboard=True, row_width=2).add(KeyboardButton("💬ChatGPT"),
                                                                          KeyboardButton("🎨Midjourney✅"),
                                                                          KeyboardButton("⚙Аккаунт"),
                                                                          KeyboardButton("👨🏻‍💻Поддержка"),
                                                                          KeyboardButton("🤝Партнерская программа"))
    else:
        return ReplyKeyboardMarkup(resize_keyboard=True, row_width=2).add(KeyboardButton("💬ChatGPT"),
                                                                          KeyboardButton("🎨Midjourney"),
                                                                          KeyboardButton("⚙Аккаунт"),
                                                                          KeyboardButton("👨🏻‍💻Поддержка"),
                                                                          KeyboardButton("🤝Партнерская программа"))

'''
# Кнопки для выбора типа подписки
sub_types = InlineKeyboardMarkup(row_width=3).add(
    InlineKeyboardButton("Базовый", callback_data="sub_type:base"),
    InlineKeyboardButton("Стандарт", callback_data="sub_type:standard"),
    InlineKeyboardButton("Премиум", callback_data="sub_type:premium"),
    InlineKeyboardButton("Иллюстратор", callback_data="sub_type:illustrator"),
    InlineKeyboardButton("Автор", callback_data="sub_type:author"),
)


# Клавиатура для выбора суммы пополнения баланса
def get_pay(user_id, stock=0):

    if stock == 0:
        stock_text = ""
    else:
        stock_text = f" (+{stock}%)"  # Если действует акция на бонусные средства
    return InlineKeyboardMarkup(row_width=3).add(
        InlineKeyboardButton("200₽" + stock_text, callback_data="select_amount:200"),
        InlineKeyboardButton("500₽" + stock_text, callback_data="select_amount:500"),
        InlineKeyboardButton("1000₽" + stock_text, callback_data="select_amount:1000")).add(
        InlineKeyboardButton("💰Другая сумма" + stock_text, callback_data="other_amount")).add(
        InlineKeyboardButton("🔙Назад", callback_data="back_to_profile:acc")
    )
'''

# Кнопки для выбора способа оплаты (Tinkoff, криптовалюта и т.д.)
def get_pay_urls(urls, order_id, src='acc'):

    return InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("Банковская карта", url=urls["tinkoff"]),
        InlineKeyboardButton("Криптовалюта", web_app=WebAppInfo(url=urls["freekassa"])),
        InlineKeyboardButton("Telegram Stars", callback_data=f"tg_stars:{order_id}"),
        InlineKeyboardButton("🔙Назад", callback_data=f"back_to_profile:{src}"))


# Клавиатура для оплаты через Telegram Stars
def get_tg_stars_pay():

    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("Telegram Stars", pay=True))  # Кнопка для оплаты через Telegram
    kb.add(InlineKeyboardButton("🔙Назад", callback_data=f"delete_msg"))  # Кнопка для возврата
    return kb


# Кнопки для управления реферальными ссылками (поделиться ссылкой, вывести средства)
def get_ref_menu(url):

    text_url = parse.quote(url)  # Кодируем URL
    url = f'https://t.me/share/url?url={text_url}'  # Формируем ссылку для поделиться
    return InlineKeyboardMarkup(row_width=1).add(InlineKeyboardButton('📩Поделится ссылкой', url=url),
                                                 InlineKeyboardButton('💳Вывод средств',
                                                                      callback_data='withdraw_ref_menu'),
                                                 InlineKeyboardButton('🔙Назад', callback_data='check_sub'))


# Кнопки для выбора изображения (вариации, зум и т.д.)
def get_try_prompt_or_choose(task_id, include_try=False):

    kb = InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("u1", callback_data=f"choose_image:{task_id}:1"),
        InlineKeyboardButton("u2", callback_data=f"choose_image:{task_id}:2"),
        InlineKeyboardButton("u3", callback_data=f"choose_image:{task_id}:3"),
        InlineKeyboardButton("u4", callback_data=f"choose_image:{task_id}:4"))
    if include_try:
        kb.add(InlineKeyboardButton("🔄 Ещё варианты", callback_data=f"try_prompt:image"))  # Кнопка для вариации запроса
    return kb


# Кнопки для изменения изображения (вариация, зум и т.д.)
def get_choose(task_id):

    return InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("🪄 Vary (Subtle)", callback_data=f"change_image:vary:low:{task_id}"),
        InlineKeyboardButton("🪄 Vary (Strong)", callback_data=f"change_image:vary:high:{task_id}"),
        InlineKeyboardButton("🔍 Zoom Out 2x", callback_data=f"change_image:zoom:2:{task_id}"),
        InlineKeyboardButton("🔍 Zoom Out 1.5x", callback_data=f"change_image:zoom:1.5:{task_id}"))

'''
# Клавиатура для уведомлений о скидках на оплату
def get_notify_pay(with_discount):

    if with_discount:
        buttons = [
            InlineKeyboardButton("Базовый", callback_data="sub_type:base:discount"),
            InlineKeyboardButton("Стандарт", callback_data="sub_type:standard:discount"),
            InlineKeyboardButton("Премиум", callback_data="sub_type:premium:discount"),
            InlineKeyboardButton("Иллюстратор", callback_data="sub_type:illustrator:discount"),
            InlineKeyboardButton("Автор", callback_data="sub_type:author:discount"),
        ]
    else:
        buttons = [
            InlineKeyboardButton("Базовый", callback_data="sub_type:base"),
            InlineKeyboardButton("Стандарт", callback_data="sub_type:standard"),
            InlineKeyboardButton("Премиум", callback_data="sub_type:premium"),
            InlineKeyboardButton("Иллюстратор", callback_data="sub_type:illustrator"),
            InlineKeyboardButton("Автор", callback_data="sub_type:author"),
        ]
    return InlineKeyboardMarkup(row_width=3).add(
        *buttons
    )


# Кнопки для выбора периода подписки
def get_sub_period(sub_type, prices, with_discount):

    btns = []
    for i, price in enumerate(prices):
        callback_data = f"sub_period:{sub_type}:{i}"
        if i != 0 and with_discount:
            callback_data += ":discount"  # Если действует скидка на определенный период
        btns.append(InlineKeyboardButton(text=price["text"], callback_data=callback_data))
    kb = InlineKeyboardMarkup(row_width=1).add(
        *btns,
        InlineKeyboardButton(text="🔙Назад", callback_data="buy_sub")
    )
    return kb
'''

''' Новые кнопки для выбора покупки токенов для GPT или MJ '''

# Кнопки выбора типа токенов
def get_neural_network_menu():

    return InlineKeyboardMarkup(row_width=2).add(
        InlineKeyboardButton("💬ChatGPT", callback_data="buy_chatgpt_tokens"),
        InlineKeyboardButton("🎨Midjourney", callback_data="buy_midjourney_requests")
    )


# Кнопки выбора количества токенов для ChatGPT
def get_chatgpt_tokens_menu():

    return InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("100 тыс токенов, 149₽", callback_data="select_chatgpt_tokens:100000:149:acc"),
        InlineKeyboardButton("200 тыс токенов, 249₽ (-20%)", callback_data="select_chatgpt_tokens:200000:249:acc"),
        InlineKeyboardButton("500 тыс токенов, 449₽ (-40%)", callback_data="select_chatgpt_tokens:500000:449:acc"),
        InlineKeyboardButton("🔙Назад", callback_data="buy_sub")
    )


# Кнопки выбора количества запросов для Midjourney
def get_midjourney_requests_menu():

    return InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("10 генераций, 149₽", callback_data="select_midjourney_requests:10:149:acc"),
        InlineKeyboardButton("20 генераций, 259₽ (-13%)", callback_data="select_midjourney_requests:20:259:acc"),
        InlineKeyboardButton("50 генераций, 599₽ (-19%)", callback_data="select_midjourney_requests:50:599:acc"),
        InlineKeyboardButton("100 генераций, 1099₽ (-26%)", callback_data="select_midjourney_requests:100:1099:acc"),
        InlineKeyboardButton("🔙Назад", callback_data="buy_sub")
    )

# Кнопки выбора количества токенов для ChatGPT СО СКИДКОЙ
def get_chatgpt_discount_tokens_menu():

    return InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("100 тыс токенов, 149₽ > 139₽ (-5%)", callback_data="select_chatgpt_tokens:100000:139:acc"),
        InlineKeyboardButton("200 тыс токенов, 249₽ > 224₽ (-10%)", callback_data="select_chatgpt_tokens:200000:224:acc"),
        InlineKeyboardButton("500 тыс токенов, 449₽ > 381₽ (-15%)", callback_data="select_chatgpt_tokens:500000:381:acc"),
        InlineKeyboardButton("🔙Назад", callback_data="buy_sub")
    )

# Кнопки выбора количества запросов для Midjourney СО СКИДКОЙ
def get_midjourney_discount_requests_menu():

    return InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("10 генераций, 149₽", callback_data="select_midjourney_requests:10:149:acc"),
        InlineKeyboardButton("20 генераций, 259₽ > 246₽ (-5%)", callback_data="select_midjourney_requests:20:246:acc"),
        InlineKeyboardButton("50 генераций, 599₽ > 550₽ (-8%)", callback_data="select_midjourney_requests:50:550:acc"),
        InlineKeyboardButton("100 генераций, 1099₽ > 989₽ (-10%)", callback_data="select_midjourney_requests:100:989:acc"),
        InlineKeyboardButton("🔙Назад", callback_data="buy_sub")
    )

    
# Кнопки выбора количества токенов для ChatGPT СО СКИДКОЙ при уведомлении
def get_chatgpt_discount_nofication():

    return InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("100 тыс токенов, 149₽ > 139₽ (-5%)", callback_data="select_chatgpt_tokens:100000:139:not_gpt"),
        InlineKeyboardButton("200 тыс токенов, 249₽ > 224₽ (-10%)", callback_data="select_chatgpt_tokens:200000:224:not_gpt"),
        InlineKeyboardButton("500 тыс токенов, 449₽ > 381₽ (-15%)", callback_data="select_chatgpt_tokens:500000:381:not_gpt")
    )

# Кнопки выбора количества запросов для Midjourney СО СКИДКОЙ при уведомлении
def get_midjourney_discount_notification():

    return InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("20 генераций, 259₽ > 246₽ (-5%)", callback_data="select_midjourney_requests:20:246:not_mj"),
        InlineKeyboardButton("50 генераций, 599₽ > 550₽ (-8%)", callback_data="select_midjourney_requests:50:550:not_mj"),
        InlineKeyboardButton("100 генераций, 1099₽ > 989₽ (-10%)", callback_data="select_midjourney_requests:100:989:not_mj")
    )