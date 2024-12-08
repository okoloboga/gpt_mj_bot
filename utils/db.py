from datetime import datetime, date, time, timedelta
import asyncpg
from asyncpg import Connection
from config import DB_USER, DB_HOST, DB_DATABASE, DB_PASSWORD


# Функция для установления соединения с базой данных
async def get_conn() -> Connection:

    return await asyncpg.connect(user=DB_USER, password=DB_PASSWORD, database=DB_DATABASE, host=DB_HOST)


# Функция для создания необходимых таблиц в базе данных, если они еще не существуют
async def start():

    conn: Connection = await get_conn()
    await conn.execute(
        "CREATE TABLE IF NOT EXISTS users("
        "user_id BIGINT PRIMARY KEY,"  # Уникальный идентификатор пользователя
        "username VARCHAR(32),"  # Имя пользователя
        "first_name VARCHAR(64),"  # Имя пользователя
        "balance INT DEFAULT 0,"  # Баланс пользователя
        "reg_time INT,"  # Время регистрации в формате timestamp
        "free_chatgpt SMALLINT DEFAULT 5000,"  # Количество бесплатных токенов для ChatGPT
        "free_image SMALLINT DEFAULT 3,"  # Количество бесплатных изображений в MidJourney
        "default_ai VARCHAR(10) DEFAULT 'empty',"  # Выбранный по умолчанию AI
        "inviter_id BIGINT,"  # ID пригласившего пользователя
        "ref_balance INT DEFAULT 0,"  # Баланс с реферальных вознаграждений
        "task_id VARCHAR(1024) DEFAULT '0',"  # ID задачи, связанной с пользователем
        "chat_gpt_lang VARCHAR(2) DEFAULT 'ru',"  # Язык для общения с ChatGPT
        "stock_time INT DEFAULT 0,"  # Время, связанное со скидками
        "new_stock_time INT DEFAULT 0,"  # Время для новых акций
        "is_pay BOOLEAN DEFAULT FALSE,"  # Флаг оплаты пользователя
        "chatgpt_about_me VARCHAR(256) DEFAULT '',"  # Информация о пользователе для ChatGPT
        "chatgpt_settings VARCHAR(256) DEFAULT '',"  # Настройки ChatGPT
        "sub_time TIMESTAMP DEFAULT NOW(),"  # Время начала подписки
        "sub_type VARCHAR(12),"  # Тип подписки
        "tokens INTEGER DEFAULT 0,"  # Количество токенов для ChatGPT
        "mj INTEGER DEFAULT 0,"  # Количество токенов для MidJourney
        "is_notified BOOLEAN DEFAULT FALSE)"  # Флаг уведомления пользователя
    )

    await conn.execute(
        "CREATE TABLE IF NOT EXISTS voice("
        "user_id BIGINT PRIMARY KEY,"
        "voice VARCHAR(64) DEFAULT 'onyx')"
    )

    await conn.execute(
        "CREATE TABLE IF NOT EXISTS usage("
        "id SERIAL PRIMARY KEY,"
        "user_id BIGINT,"
        "ai_type VARCHAR(10),"
        "image_type VARCHAR(10),"
        "use_time INT,"
        "get_response BOOLEAN DEFAULT FALSE,"
        "create_time TIMESTAMP DEFAULT NOW(),"
        "external_task_id VARCHAR(1024))"
    )

    await conn.execute(
        "CREATE TABLE IF NOT EXISTS withdraws(id SERIAL PRIMARY KEY, user_id BIGINT, amount INT, withdraw_time INT)")

    await conn.execute("CREATE TABLE IF NOT EXISTS config(config_key VARCHAR(32), config_value VARCHAR(256))")

    await conn.execute("CREATE TABLE IF NOT EXISTS promocode("
                       "promocode_id SMALLSERIAL,"  # Уникальный идентификатор промокода
                       "amount INTEGER,"  # Сумма, которая может быть получена по промокоду
                       "uses_count SMALLINT,"  # Количество использований промокода
                       "code VARCHAR(10) UNIQUE)")  # Сам код промокода

    await conn.execute("CREATE TABLE IF NOT EXISTS user_promocode("
                       "promocode_id SMALLINT,"  # ID промокода
                       "user_id BIGINT)")  # ID пользователя, связанного с промокодом
    
    # await conn.execute(
    #     "CREATE TABLE IF NOT EXISTS sub_orders("
    #     "sub_order_id SERIAL,"  # Уникальный идентификатор подписки
    #     "user_id BIGINT,"  # ID пользователя
    #     "amount INTEGER,"  # Сумма подписки
    #     "create_time TIMESTAMP DEFAULT NOW(),"  # Время создания подписки
    #     "pay_time TIMESTAMP,"  # Время оплаты подписки
    #     "sub_type VARCHAR(12),"  # Тип подписки
    #     "days INTEGER,"  # Количество дней подписки
    #     "with_discount BOOLEAN DEFAULT FALSE)"  # Наличие скидки
    # )

    await conn.execute(
        "CREATE TABLE IF NOT EXISTS orders("
        "id SERIAL PRIMARY KEY,"  # Уникальный идентификатор заказа
        "user_id BIGINT,"  # ID пользователя
        "amount INT,"  # Сумма покупки
        "order_type VARCHAR(10),"  # Тип заказа: 'chatgpt' или 'midjourney'
        "quantity INT,"  # Количество токенов или запросов
        "create_time TIMESTAMP DEFAULT NOW(),"  # Время создания заказа
        "pay_time TIMESTAMP)"  # Время оплаты заказа
    )

    await conn.execute(
        "CREATE TABLE IF NOT EXISTS discount_gpt ("
        "user_id BIGINT PRIMARY KEY,"           # Уникальный идентификатор пользователя
        "is_notified BOOLEAN DEFAULT FALSE,"    # Статус уведомления
        "last_notification TIMESTAMP,"           # Дата и время последнего уведомления
        "used BOOLEAN DEFAULT FALSE)"           # Статус использования скидки
    )

    await conn.execute(
        "CREATE TABLE IF NOT EXISTS discount_mj ("
        "user_id BIGINT PRIMARY KEY,"           # Уникальный идентификатор пользователя
        "is_notified BOOLEAN DEFAULT FALSE,"    # Статус уведомления
        "last_notification TIMESTAMP,"           # Дата и время последнего уведомления
        "used BOOLEAN DEFAULT FALSE)"           # Статус использования скидки
    )

    # Проверяем наличие токена конфигурации, и если его нет - добавляем значение по умолчанию
    row = await conn.fetchrow("SELECT config_value FROM config WHERE config_key = 'iam_token'")
    if row is None:
        await conn.execute("INSERT INTO config VALUES('iam_token', '1')")
    await conn.close()


# Функция для получения всех пользователей
async def get_users():

    conn: Connection = await get_conn()
    rows = await conn.fetch("SELECT user_id FROM users")
    await conn.close()
    return rows


# Функция для получения информации о пользователе по user_id
async def get_user(user_id):

    conn: Connection = await get_conn()
    row = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
    await conn.close()
    return row


# Получение информации о выранном голосе
async def get_voice(user_id):
    conn: Connection = await get_conn()
    row = await conn.fetchrow("SELECT voice FROM voice WHERE user_id = $1", user_id)
    await conn.close()
    return row["voice"] if row else 'onyx'  # Возвращаем только значение или None


# Записываем выбранный голос в базу данных
async def set_voice(user_id, voice):

    conn: Connection = await get_conn()
    await conn.execute("UPDATE voice SET voice = $2 WHERE user_id = $1", user_id, voice)
    await conn.close()

# Записываем нового пользователя с голосами в базу данных
async def create_voice(user_id, voice='onyx'):

    conn: Connection = await get_conn()
    await conn.execute(
        "INSERT INTO voice(user_id, voice) VALUES ($1, $2)", 
        user_id, voice)
    await conn.close()
    return "onyx"

# Функция для добавления нового пользователя
async def add_user(user_id, username, first_name, inviter_id):

    conn: Connection = await get_conn()
    await conn.execute(
        "INSERT INTO users(user_id, username, first_name, reg_time, inviter_id, free_image) VALUES ($1, $2, $3, $4, $5, 3)",
        user_id, username, first_name, int(datetime.now().timestamp()), inviter_id)
    await conn.close()


# Функция для обновления task_id пользователя
async def update_task_id(user_id, task_id):

    conn: Connection = await get_conn()
    await conn.execute("UPDATE users SET task_id = $2 WHERE user_id = $1", user_id, task_id)
    await conn.close()


# Функция для обновления флага оплаты пользователя
async def update_is_pay(user_id, is_pay):

    conn: Connection = await get_conn()
    await conn.execute("UPDATE users SET is_pay = $2 WHERE user_id = $1", user_id, is_pay)
    await conn.close()


# Функция для обновления информации о пользователе для ChatGPT
async def update_chatgpt_about_me(user_id, text):

    conn: Connection = await get_conn()
    await conn.execute("UPDATE users SET chatgpt_about_me = $2 WHERE user_id = $1", user_id, text)
    await conn.close()


# Функция для обновления настроек ChatGPT пользователя
async def update_chatgpt_settings(user_id, text):

    conn: Connection = await get_conn()
    await conn.execute("UPDATE users SET chatgpt_settings = $2 WHERE user_id = $1", user_id, text)
    await conn.close()


# Функция для изменения AI по умолчанию для пользователя
async def change_default_ai(user_id, ai_type):

    conn: Connection = await get_conn()
    await conn.execute("UPDATE users SET default_ai = $2 WHERE user_id = $1", user_id, ai_type)
    await conn.close()


# Функция для уменьшения количества бесплатных токенов ChatGPT для пользователя
async def remove_free_chatgpt(user_id, tokens):

    conn: Connection = await get_conn()
    await conn.execute("UPDATE users SET free_chatgpt = free_chatgpt - $2 WHERE user_id = $1", user_id, tokens)
    await conn.close()


# Функция для уменьшения количества токенов ChatGPT у пользователя
async def remove_chatgpt(user_id, tokens):

    conn: Connection = await get_conn()
    await conn.execute("UPDATE users SET tokens = tokens - $2 WHERE user_id = $1", user_id, tokens)
    await conn.close()


# Функция для уменьшения количества бесплатных изображений у пользователя
async def remove_free_image(user_id):

    conn: Connection = await get_conn()
    await conn.execute("UPDATE users SET free_image = free_image - 1 WHERE user_id = $1", user_id)
    await conn.close()


# Функция для уменьшения количества токенов MidJourney у пользователя
async def remove_image(user_id):

    conn: Connection = await get_conn()
    await conn.execute("UPDATE users SET mj = mj - 1 WHERE user_id = $1", user_id)
    await conn.close()


# Функция для обновления времени акций у пользователя
async def update_stock_time(user_id, stock_time):

    conn: Connection = await get_conn()
    await conn.execute("UPDATE users SET stock_time = $2 WHERE user_id = $1", user_id, stock_time)
    await conn.close()


# Функция для обновления нового времени акций у пользователя
async def update_new_stock_time(user_id, new_stock_time):

    conn: Connection = await get_conn()
    await conn.execute("UPDATE users SET new_stock_time = $2 WHERE user_id = $1", user_id, new_stock_time)
    await conn.close()


# Функция для уменьшения баланса пользователя на фиксированное значение (10)
async def remove_balance(user_id):

    conn: Connection = await get_conn()
    await conn.execute("UPDATE users SET balance = balance - 10 WHERE user_id = $1", user_id)
    await conn.close()


# Функция для добавления баланса пользователю администратором
async def add_balance_from_admin(user_id, amount):

    conn: Connection = await get_conn()
    await conn.execute("UPDATE users SET balance = balance + $2 WHERE user_id = $1", user_id, amount)
    await conn.close()


# Функция для добавления баланса пользователю и начисления реферального бонуса, если это не промоакция
async def add_balance(user_id, amount, is_promo=False):

    conn: Connection = await get_conn()
    ref_balance = int(float(amount) * 0.15)
    await conn.execute("UPDATE users SET balance = balance + $2 WHERE user_id = $1", user_id, amount)
    if not is_promo:
        await conn.execute(
            "UPDATE users SET ref_balance = ref_balance + $2 WHERE user_id = (SELECT inviter_id FROM users WHERE user_id = $1)",
            user_id, ref_balance)
    await conn.close()

# Проверка наличия активного заказа со скидкой для пользователя
async def check_discount_order(user_id):

    conn: Connection = await get_conn()
    row = await conn.fetchrow("SELECT * FROM sub_orders WHERE user_id = $1 and with_discount = TRUE", user_id)
    await conn.close()
    return row


# Добавление баланса пользователю за счет реферального баланса
async def add_balance_from_ref(user_id):

    conn: Connection = await get_conn()
    await conn.execute("UPDATE users SET balance = balance + ref_balance, ref_balance = 0 WHERE user_id = $1",
                       user_id)
    await conn.close()


# Изменение языка ChatGPT для пользователя
async def change_chat_gpt_lang(user_id, new_lang):

    conn: Connection = await get_conn()
    await conn.execute("UPDATE users SET chat_gpt_lang = $2 WHERE user_id = $1",
                       user_id, new_lang)
    await conn.close()


# Получение языка ChatGPT для пользователя
async def get_chat_gpt_lang(user_id):
    conn: Connection = await get_conn()
    
    try:
        # Выполняем запрос для получения языка
        result = await conn.fetchval(
            "SELECT chat_gpt_lang FROM users WHERE user_id = $1",
            user_id
        )
        return result  # Возвращаем язык
    except Exception as e:
        logger.error(f"Ошибка при получении языка пользователя {user_id}: {e}")
        raise e
    finally:
        await conn.close()


# Получение статистики по рефералам для пользователя
async def get_ref_stat(user_id):
    conn: Connection = await get_conn()
    row = await conn.fetchrow("SELECT (SELECT CAST(sum(amount) * 0.15 as int) FROM sub_orders WHERE "
                              "EXISTS(SELECT * FROM users "
                              "WHERE inviter_id = $1 AND users.user_id = sub_orders.user_id)) as all_income,"
                              "(SELECT ref_balance FROM users WHERE user_id = $1) as available_for_withdrawal,"
                              "(SELECT COUNT(user_id) FROM users WHERE inviter_id = $1) as count_refs,"
                              "(SELECT COUNT(sub_order_id) FROM sub_orders JOIN users u ON sub_orders.user_id = u.user_id WHERE u.inviter_id = $1) as orders_count",
                              user_id)
    await conn.close()
    return row


# Получение всех пользователей, которые являются пригласившими
async def get_all_inviters():

    conn: Connection = await get_conn()
    rows = await conn.fetch('select distinct inviter_id from users where inviter_id != 0')
    await conn.close()
    return rows


# Добавление действия пользователя (использование AI)
async def add_action(user_id, ai_type, image_type=''):

    conn: Connection = await get_conn()
    action = await conn.fetchrow("INSERT INTO usage(user_id, ai_type, image_type) VALUES ($1, $2, $3) RETURNING id",
                                 user_id, ai_type, image_type)
    await conn.close()
    return action["id"]


# Получение информации о действии по его ID
async def get_action(action_id):

    conn: Connection = await get_conn()
    row = await conn.fetchrow("SELECT * FROM usage WHERE id = $1", action_id)
    await conn.close()
    return row


# Установка связи между task_id и action_id
async def update_action_with_task_id(request_id, task_id):
    conn: Connection = await get_conn()
    await conn.execute(
        "UPDATE usage SET external_task_id = $1 WHERE id = $2",
        task_id, request_id
    )
    await conn.close()


# Получение информации о действии по task_id
async def get_action_by_task_id(task_id):
    conn: Connection = await get_conn()
    row = await conn.fetchrow("SELECT * FROM usage WHERE external_task_id = $1", task_id)
    await conn.close()
    return row



# Получение информации о действии по action_id
async def get_task_by_action_id(action_id):
    conn: Connection = await get_conn()
    row = await conn.fetchrow("SELECT external_task_id FROM usage WHERE id = $1", action_id)
    await conn.close()
    return row


# Установка флага, что ответ на действие пользователя был получен
async def set_action_get_response(usage_id):

    conn: Connection = await get_conn()
    await conn.execute("UPDATE usage SET get_response = TRUE WHERE id = $1", usage_id)
    await conn.close()


# Получение общей статистики
async def get_stat():

    end = datetime.now()
    start = datetime.combine(date.today(), datetime.min.time())

    old_end = int(end.timestamp())
    old_start = int(start.timestamp())

    conn: Connection = await get_conn()
    row = await conn.fetchrow("SELECT (SELECT COUNT(*) FROM users) as users_count,"
                              "(SELECT COUNT(*) FROM users where reg_time between $3 and $4) as today_users_count,"
                              "(SELECT COUNT(*) FROM usage WHERE ai_type = 'chatgpt') as chatgpt_count,"
                              "(SELECT COUNT(*) FROM usage WHERE ai_type = 'image') as image_count,"
                              "(SELECT COUNT(*) FROM usage WHERE ai_type = 'chatgpt' and create_time between $1 and $2) "
                              "as today_chatgpt_count,"
                              "(SELECT COUNT(*) FROM usage WHERE ai_type = 'image' and create_time between $1 and $2) "
                              "as today_image_count",
                              start, end, old_start, old_end)
    await conn.close()
    return row


# Получение IAM токена из таблицы конфигурации
async def get_iam_token():

    conn: Connection = await get_conn()
    row = await conn.fetchrow("SELECT config_value FROM config WHERE config_key = 'iam_token'")
    await conn.close()
    return row['config_value']


# Изменение IAM токена
async def change_iam_token(iam_token):

    conn: Connection = await get_conn()
    await conn.execute(
        "UPDATE config SET config_value = $1 WHERE config_key = 'iam_token'", iam_token)
    await conn.close()


# Добавление нового вывода средств
async def add_withdraw(user_id, amount):

    conn: Connection = await get_conn()
    await conn.execute("INSERT INTO withdraws(user_id, amount, withdraw_time) VALUES ($1, $2, $3)",
                       user_id, amount, int(datetime.now().timestamp()))
    await conn.close()


# Сброс реферального баланса пользователя
async def reset_ref_balance(user_id):

    conn: Connection = await get_conn()
    await conn.execute(
        "UPDATE users SET ref_balance = 0 WHERE user_id = $1", user_id)
    await conn.close()


# Создание нового промокода
async def create_promocode(amount, uses_count, code):

    conn: Connection = await get_conn()
    await conn.execute(
        "INSERT INTO promocode(amount, uses_count, code) VALUES ($1, $2, $3)", amount, uses_count, code)
    await conn.close()


# Получение промокода по его коду
async def get_promocode_by_code(code):

    conn: Connection = await get_conn()
    row = await conn.fetchrow("SELECT * FROM promocode WHERE code = $1", code)
    await conn.close()
    return row


# Создание промокода для пользователя
async def create_user_promocode(promocode_id, user_id):

    conn: Connection = await get_conn()
    await conn.execute(
        "INSERT INTO user_promocode(promocode_id, user_id) VALUES ($1, $2)", promocode_id, user_id)
    await conn.close()


# Получение пользовательского промокода по его ID и ID пользователя
async def get_user_promocode_by_promocode_id_and_user_id(promocode_id, user_id):

    conn: Connection = await get_conn()
    row = await conn.fetchrow("SELECT * FROM user_promocode WHERE promocode_id = $1 and user_id = $2", promocode_id,
                              user_id)
    await conn.close()
    return row


# Получение всех промокодов пользователя по его ID
async def get_all_user_promocode_by_promocode_id(promocode_id):

    conn: Connection = await get_conn()
    rows = await conn.fetch("SELECT * FROM user_promocode WHERE promocode_id = $1", promocode_id)
    await conn.close()
    return rows


# Получение статистики по промокодам
async def get_promo_for_stat():

    conn: Connection = await get_conn()
    rows = await conn.fetch("""select code, amount, uses_count, count(up.user_id) as users_count
from promocode
         left join user_promocode up on promocode.promocode_id = up.promocode_id
group by promocode.promocode_id, amount, uses_count, code
having count(up.user_id) < uses_count""")
    await conn.close()
    return rows


""" НОВЫЕ ФУНКЦИИ ТОКЕНОВ И ЗАПРОСОВ """
""" Заказы токенов и запросов"""


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


async def get_sub_stat():
    conn: Connection = await get_conn()
    row = await conn.fetchrow("SELECT "
                              "COUNT(*) FILTER (WHERE sub_type = 'base') as base,"
                              "COUNT(*) FILTER (WHERE sub_type = 'standard') as standard,"
                              "COUNT(*) FILTER (WHERE sub_type = 'premium') as premium "
                              "FROM users where sub_time > NOW()")
    await conn.close()
    return row


async def get_today_sub_stat():
    conn: Connection = await get_conn()
    row = await conn.fetchrow("SELECT "
                              "COUNT(*) FILTER (WHERE sub_type = 'base') as base,"
                              "COUNT(*) FILTER (WHERE sub_type = 'standard') as standard,"
                              "COUNT(*) FILTER (WHERE sub_type = 'premium') as premium "
                              "FROM sub_orders WHERE pay_time is not null and pay_time::date = current_date"
                              )
    await conn.close()
    return row

"""Скидка ChatGPT"""

async def get_user_notified_gpt(user_id):
    conn: Connection = await get_conn()
    row = await conn.fetchrow(
        "SELECT is_notified, last_notification, used FROM discount_gpt WHERE user_id = $1", 
        user_id)
    await conn.close()
    return row

async def create_user_notification_gpt(user_id):
    """Создаем новую запись уведомления для пользователя."""
    conn: Connection = await get_conn()
    await conn.execute(
        """
        INSERT INTO discount_gpt (user_id, is_notified, last_notification) 
        VALUES ($1, TRUE, NOW()) 
        ON CONFLICT (user_id) 
        DO UPDATE SET is_notified = TRUE, last_notification = NOW()
        """,
        user_id
    )
    await conn.close()

async def update_user_notification_gpt(user_id):
    """Обновляем уведомление пользователя, если запись уже существует."""
    conn: Connection = await get_conn()
    await conn.execute(
        "UPDATE discount_gpt SET is_notified = TRUE, last_notification = NOW() WHERE user_id = $1",
        user_id)
    await conn.close()

async def update_used_discount_gpt(user_id):
    conn: Connection = await get_conn()
    await conn.execute(
        "UPDATE discount_gpt SET used = TRUE WHERE user_id = $1",
        user_id)
    await conn.close()

"""Скидка Midjourney"""

async def get_user_notified_mj(user_id):
    conn: Connection = await get_conn()
    row = await conn.fetchrow(
        "SELECT is_notified, last_notification, used FROM discount_mj WHERE user_id = $1", 
        user_id)
    await conn.close()
    return row

async def create_user_notification_mj(user_id):
    """Создаем новую запись уведомления для пользователя."""
    conn: Connection = await get_conn()
    await conn.execute(
        """
        INSERT INTO discount_mj (user_id, is_notified, last_notification) 
        VALUES ($1, TRUE, NOW()) 
        ON CONFLICT (user_id) 
        DO UPDATE SET is_notified = TRUE, last_notification = NOW()
        """,
        user_id
    )
    await conn.close()

async def update_user_notification_mj(user_id):
    """Обновляем уведомление пользователя, если запись уже существует."""
    conn: Connection = await get_conn()
    await conn.execute(
        "UPDATE discount_mj SET is_notified = TRUE, last_notification = NOW() WHERE user_id = $1",
        user_id)
    await conn.close()

async def update_used_discount_mj(user_id):
    conn: Connection = await get_conn()
    await conn.execute(
        "UPDATE discount_mj SET used = TRUE WHERE user_id = $1",
        user_id)
    await conn.close()


async def get_orders_statistics(period: str = "all"):
    """
    Получает статистику заказов за указанный период.
    
    :param period: Период статистики: '24h', 'month', или 'all'.
    :return: Словарь с данными статистики.
    """
    conn: Connection = await get_conn()

    # Определяем временной фильтр на основе периода
    now = datetime.now()
    if period == "24h":
        start_time = now - timedelta(hours=24)
    elif period == "month":
        start_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start_time = None  # Для 'all' нет ограничения по времени

    # Основной SQL-запрос с условием времени
    query = """
    SELECT 
        order_type,
        quantity,
        COUNT(*) AS count,
        SUM(amount) AS total_amount
    FROM orders
    WHERE pay_time IS NOT NULL
    """
    
    # Добавляем фильтрацию по времени, если указано
    if start_time:
        query += " AND pay_time >= $1"

    query += " GROUP BY order_type, quantity ORDER BY order_type, quantity;"

    # Выполняем запрос
    if start_time:
        rows = await conn.fetch(query, start_time)
    else:
        rows = await conn.fetch(query)

    await conn.close()
    
    # Организуем данные в удобный для обработки формат
    stats = {}
    for row in rows:
        order_type = row['order_type']
        if order_type not in stats:
            stats[order_type] = {}
        stats[order_type][row['quantity']] = {
            'count': row['count'],
            'total_amount': row['total_amount']
        }
    
    return stats
