# Используем официальный образ Python
FROM python:3.10-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y build-essential libpq-dev

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем файлы requirements.txt в контейнер
COPY requirements.txt .

# Устанавливаем Python-зависимости
RUN pip install --upgrade pip && pip install -r requirements.txt

# Копируем все файлы проекта в контейнер
COPY . .

# Указываем команду по умолчанию для запуска приложения
CMD ["python", "main.py"]
