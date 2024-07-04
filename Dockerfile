# Используем официальный базовый образ Python 3.11
FROM python:3.11-slim

# Устанавливаем зависимости для библиотеки sqlite и других необходимых пакетов
RUN apt-get update && apt-get install -y \
    sqlite3 \
    && apt-get clean

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл requirements.txt и устанавливаем зависимости
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Копируем оставшиеся файлы проекта
COPY . .

# Указываем переменные окружения
ENV API_TOKEN=7235202091:AAEkO5yb0EqieqRueQBNyhzFWIIbEzuyF_c

# Запускаем бота
CMD ["python", "telegram.py"]