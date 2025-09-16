#Используем официальный образ Python
FROM python:3.10-slim

#Установка рабочей директории
WORKDIR /app

#Копирование и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

#Копируем исходный код
COPY . .

#Запускаем бота
CMD ["python", "Bot_tale.py"]
