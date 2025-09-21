#Используем официальный образ Python
FROM python:3.10-slim

#Создание и установка рабочей директории
RUN mkdir /bot				#Создание директории /bot внутри контейнера
WORKDIR /bot				# установка /bot как рабочую директорию

#Настройка переменных окружения
ENV PYTHONDONTWRITEBYTECODE 1		#Запрет Python  создавать .pyc файлы для ускорения запуска
ENV PYTHONUNBUFFERED 1			#Отключение буферизации вывода Python

#Копирование и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

#Копируем исходный код
COPY . .
