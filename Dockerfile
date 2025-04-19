FROM python:3.12:slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    build-essential gcc libpq-dev curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Создание рабочей директории
WORKDIR /app

# Установка Poetry (по желанию можно на pip)
RUN pip install --upgrade pip && pip install poetry

# Копирование зависимостей и установка
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --only main

# Копируем весь код
COPY . .

# Команда запуска (будет переопределяться в docker-compose)
CMD ["python", "main.py"]
