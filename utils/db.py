from datetime import datetime, date, time, timedelta
import asyncpg
from asyncpg import Connection
from config import DB_USER, DB_HOST, DB_DATABASE, DB_PASSWORD


# Получение подключения к базе данных
async def get_conn() -> Connection:
    return await asyncpg.connect(user=DB_USER, password=DB_PASSWORD, database=DB_DATABASE, host=DB_HOST)


# Инициализация базы данных: создание таблиц, если они не существуют
async def start():
    conn: Connection = await get_conn()
    await conn.execute(
        "CREATE TABLE IF NOT EXISTS users("
        "user_id BIGINT PRIMARY KEY,"  # ID пользователя
        "username VARCHAR(32),"  # Имя пользователя
        "first_name VARCHAR(64),"  # Имя
        "balance INT DEFAULT 0,"  # Баланс пользователя
        "reg_time INT,"  # Время регистрации (timestamp)
        "free_chatgpt SMALLINT DEFAULT 10000,"  # Бесплатные токены для ChatGPT
        "free_image SMALLINT DEFAULT 10,"  # Бесплатные изображения для MidJourney
        "default_ai VARCHAR(10) DEFAULT 'empty',"  # По умолчанию выбранный AI
        "inviter_id BIGINT,"  # ID пользователя, пригласившего данного юзера
        "ref_balance INT DEFAULT 0,"  # Баланс для реферальных выплат
        "task_id VARCHAR(1024) DEFAULT '0',"  # ID задачи
        "chat_gpt_lang VARCHAR(2) DEFAULT 'ru',"  # Язык для ChatGPT
        "stock_time INT DEFAULT 0,"  # Время начала акции
        "new_stock_time INT DEFAULT 0,"  # Время окончания акции
        "is_pay BOOLEAN DEFAULT FALSE,"  # Флаг, указывающий на платного пользователя
        "chatgpt_about_me VARCHAR(256) DEFAULT '',"  # Информация о пользователе для ChatGPT
        "chatgpt_settings VARCHAR(256) DEFAULT '',"  # Настройки ChatGPT
        "sub_time TIMESTAMP DEFAULT NOW(),"  # Время окончания подписки
        "sub_type VARCHAR(12),"  # Тип подписки
        "tokens INTEGER DEFAULT 0,"  # Количество токенов
        "mj INTEGER DEFAULT 0,"  # Количество изображений для MidJourney
        "is_notified BOOLEAN DEFAULT FALSE)"  # Уведомлялся ли пользователь
    )
    
    # Создание таблицы заказов
    await conn.execute("CREATE TABLE IF NOT EXISTS orders(id SERIAL PRIMARY KEY, user_id BIGINT, amount INT, stock INT,"
                       "pay_time INT)")
    
    # Создание таблицы использования AI-услуг
    await conn.execute(
        "CREATE TABLE IF NOT EXISTS usage(id SERIAL PRIMARY KEY, user_id BIGINT, ai_type VARCHAR(10), use_time INT,"
        "get_response BOOLEAN DEFAULT FALSE)")

    # Создание таблицы для выводов средств
    await conn.execute(
        "CREATE TABLE IF NOT EXISTS withdraws(id SERIAL PRIMARY KEY, user_id BIGINT, amount INT, withdraw_time INT)")

    # Конфигурационная таблица
    await conn.execute("CREATE TABLE IF NOT EXISTS config(config_key VARCHAR(32), config_value VARCHAR(256))")

    # Таблица промокодов
    await conn.execute("CREATE TABLE IF NOT EXISTS promocode("
                       "promocode_id SMALLSERIAL,"
                       "amount INTEGER,"
                       "uses_count SMALLINT,"
                       "code VARCHAR(10) UNIQUE)")

    # Таблица для отслеживания использованных промокодов
    await conn.execute("CREATE TABLE IF NOT EXISTS user_promocode("
                       "promocode_id SMALLINT,"
                       "user_id BIGINT)")
    
    ''' Не нужна, так как подписок больше нет

    # Таблица заказов подписок
    await conn.execute(
        "CREATE TABLE IF NOT EXISTS sub_orders("
        "sub_order_id SERIAL,"
        "user_id BIGINT,"
        "amount INTEGER,"
        "create_time TIMESTAMP DEFAULT NOW(),"  # Время создания заказа
        "pay_time TIMESTAMP,"  # Время оплаты
        "sub_type VARCHAR(12),"  # Тип подписки
        "days INTEGER,"  # Количество дней подписки
        "with_discount BOOLEAN DEFAULT FALSE)"  # Есть ли скидка
    )
    '''

    await conn.execute(
        "CREATE TABLE IF NOT EXISTS orders("
        "id SERIAL PRIMARY KEY,"  # Уникальный идентификатор заказа
        "user_id BIGINT,"  # ID пользователя
        "amount INT,"  # Сумма покупки
        "order_type VARCHAR(10),"  # Тип заказа: 'chatgpt' или 'midjourney'
        "quantity INT,"  # Количество токенов или запросов
        "create_time TIMESTAMP DEFAULT NOW(),"  # Время создания заказа
        "pay_time TIMESTAMP)"  # Время оплаты
    )
    
    # Проверка наличия IAM токена, если его нет — создание
    row = await conn.fetchrow("SELECT config_value FROM config WHERE config_key = 'iam_token'")
    if row is None:
        await conn.execute("INSERT INTO config VALUES('iam_token', '1')")
    await conn.close()


# Получение списка всех пользователей
async def get_users():

    conn: Connection = await get_conn()
    rows = await conn.fetch("SELECT user_id FROM users")
    await conn.close()
    return rows


# Получение информации о пользователе по его ID
async def get_user(user_id):

    conn: Connection = await get_conn()
    row = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
    await conn.close()
    return row


# Добавление нового пользователя
async def add_user(user_id, username, first_name, inviter_id):

    conn: Connection = await get_conn()
    await conn.execute(
        "INSERT INTO users(user_id, username, first_name, reg_time, inviter_id, free_image) VALUES ($1, $2, $3, $4, $5, 10)",
        user_id, username, first_name, int(datetime.now().timestamp()), inviter_id)
    await conn.close()

""" Стырае функции для работы с подписками

# Обновление информации о подписке пользователя
async def update_sub_info(user_id, sub_time, sub_type, tokens, mj):
    conn: Connection = await get_conn()
    await conn.execute(
        "UPDATE users SET sub_time = $2, sub_type = $3, tokens = $4, mj = $5, is_notified = FALSE WHERE user_id = $1",
        user_id, sub_time, sub_type, tokens, mj)
    await conn.close()

# Установка времени оплаты для заказа подписки
async def set_sub_order_pay(sub_order_id):
    conn: Connection = await get_conn()
    await conn.execute("UPDATE sub_orders SET pay_time = NOW() WHERE sub_order_id = $1", sub_order_id)
    await conn.close()

# Добавление заказа подписки
async def add_sub_order(user_id, amount, sub_type, discount, days):
    conn: Connection = await get_conn()
    row = await conn.fetchrow(
        "INSERT INTO sub_orders(user_id, amount, sub_type, with_discount, days) VALUES ($1, $2, $3, $4, $5) RETURNING *",
        user_id, amount, sub_type, discount, days)
    await conn.close()
    return row["sub_order_id"]

# Получение информации о заказе подписки
async def get_sub_order(sub_order_id):
    conn: Connection = await get_conn()
    row = await conn.fetchrow("SELECT * FROM sub_orders WHERE sub_order_id = $1", sub_order_id)
    await conn.close()
    return row

"""


# Добавление заказа на покупку токенов или запросов
async def add_token_or_request_order(user_id, amount, item_type, quantity, discount=False):

    conn: Connection = await get_conn()
    row = await conn.fetchrow(
        """
        INSERT INTO orders (user_id, item_type, quantity, amount, status, discount, create_time)
        VALUES ($1, $2, $3, $4, 'pending', $5, NOW())
        RETURNING order_id
        """,
        user_id, item_type, quantity, amount, discount
    )
    await conn.close()
    return row["order_id"]


""" Заказы """

# Добавление нового заказа на токены/запросы
async def add_order(user_id, amount, order_type, quantity):

    conn: Connection = await get_conn()
    row = await conn.fetchrow(
        "INSERT INTO orders(user_id, amount, order_type, quantity, pay_time) VALUES ($1, $2, $3, $4, NULL) RETURNING *",
        user_id, amount, order_type, quantity)
    await conn.close()
    return row["id"]


# Получение информации о заказе по ID
async def get_order(order_id):

    conn: Connection = await get_conn()
    row = await conn.fetchrow("SELECT * FROM orders WHERE id = $1", order_id)
    await conn.close()
    return row


# Установка времени оплаты для заказа
async def set_order_pay(order_id):

    conn: Connection = await get_conn()
    await conn.execute("UPDATE orders SET pay_time = NOW() WHERE id = $1", order_id)
    await conn.close()


''' Токены и Запросы '''

# Обновление количества токенов у пользователя
async def update_tokens(user_id, new_tokens):

    conn: Connection = await get_conn()
    await conn.execute("UPDATE users SET tokens = $2 WHERE user_id = $1", user_id, new_tokens)
    await conn.close()


# Обновление количества запросов MidJourney у пользователя
async def update_requests(user_id, new_requests):

    conn: Connection = await get_conn()
    await conn.execute("UPDATE users SET mj = $2 WHERE user_id = $1", user_id, new_requests)
    await conn.close()


