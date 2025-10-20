'''Мощный генератор сказок'''

import os
import asyncio
import aiohttp
import json
import csv
import datetime
from pathlib import Path
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv
from aiohttp import ClientTimeout
from speechkit import init_tts_manager

load_dotenv()

#Конфигурация
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

#Установка таймаута для запросов
TIMEOUT = ClientTimeout(total=30)		#30 сек

bot=Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

'''Хранение данных пользователя'''
user_data = {}

#Создание папки data для хранения статистики если она не существует
DATA_DIR = "/bot/data"
os.makedirs(DATA_DIR, exist_ok=True)

"""++++++++++++++СТАТИСТИКА++++++++++++++"""
STATS_FILE = os.path.join(DATA_DIR,"user_stats.csv")
TALE_STATS_FILE = os.path.join(DATA_DIR,"tale_stats.csv")

AGE_GROUP_NAMES = {"1":"1-2 года",
   		   "2":"3-5 лет",
   		   "3":"6-8 лет"}

#Инициализация файлов статистики
def init_stats_files():			
   
   #Файл статистики пользователей
   if not Path(STATS_FILE).exists():			#Проверка существует файл или нет
      with open(STATS_FILE, 'w', newline = '', encoding = 'utf-8') as f:
         writer = csv.writer(f)				#Создать новый файл, если он не найден
         
         writer.writerow(['user_id', 'username','first_name', 'last_name',
		 'first_seen', 'last_seen', 'tales_generated'])	#Записать строку заголовков

   #Файл статистики сказок
   if not Path(TALE_STATS_FILE).exists():		#Проверка существует файл или нет
      with open(TALE_STATS_FILE, 'w', newline = '', encoding = 'utf-8') as f:
         writer = csv.writer(f)				#Создать новый файл, если он не найден

         writer.writerow(['timestamp', 'user_id', 'age_group',
		 'genre', 'style','location', 'hero',
		 'enemy', 'child_name', 'gender',
		 'audio_requested', 'voice_type'])	#Записать строку заголовков
		 
#Обновление статистики пользователя
def update_user_stats(user: types.User):
   user_id = user.id
   username = user.username or "N/A"
   first_name = user.first_name or "N/A"
   last_name = user.last_name or "N/A"
   current_time = datetime.datetime.now().isoformat()	#Получение даты и прео-е в строку

   #Читаем существующую статистику
   users = {}
   if Path(STATS_FILE).exists():
      with open(STATS_FILE, 'r', newline = '', encoding = 'utf-8') as f:
         reader = csv.DictReader(f)	#DictReader исп-ет 1-ю строку ф-ла, как заголовки столбцов
         for row in reader:		#Пройти по строкам
            users[row['user_id']] = row	#Сохраняем данные пользователя в словарь users

   #Обновляем данные пользователя
   if str(user_id) in users:
      users[str(user_id)]['last_seen'] = current_time
      users[str(user_id)]['tales_generated'] = str(int(users
      [str(user_id)].get('tales_generated', 0)) + 1)
   else:
      users[str(user_id)] = {'user_id': str(user_id),
      			'username': username,
      			'first_name': first_name,
      			'last_name': last_name,
      			'first_seen': current_time,
      			'last_seen': current_time,
      			'tales_generated': '1'}
      			
   #Записываем обновленные данные
   with open(STATS_FILE, 'w', newline = '', encoding = 'utf-8') as f:
      writer = csv.DictWriter(f, fieldnames = 
      		['user_id', 'username', 'first_name',
      		 'last_name', 'first_seen', 'last_seen',
      		 'tales_generated'])
      writer.writeheader()
      for user_data in users.values():
         writer.writerow(user_data)
         
#Запись статистики сказки
def log_tale_generation(user_id, tale_data):
   timestamp = datetime.datetime.now().isoformat()	#Получение тек. даты и времени
   audio_requested = "yes" if tale_data.get("audio_requested") else "no"
   voice_type = tale_data.get("voice_type", "N/A")
   
   with open(TALE_STATS_FILE, 'a', newline = '', encoding='utf-8') as f:
      writer = csv.writer(f)			#создание объекта writer для записи данных в файл
      writer.writerow([timestamp, user_id, 		#Время генерации сказки, id пользователя
      			 tale_data.get('age', 'N/A'),	#Возрастная группа
      			 tale_data.get('genre', 'N/A'),	
      			 tale_data.get('style', 'N/A'),
      			 tale_data.get('location', 'N/A'),
      			 tale_data.get('hero', 'N/A'),
      			 tale_data.get('enemy', 'N/A'),
      			 tale_data.get('child_name', 'N/A'),
      			 tale_data.get('gender', 'N/A'),
      			 audio_requested,
      			 voice_type])
      			 	
#Команда для просмотра статистики (ТОЛЬКО ДЛЯ АДМИНИСТРАТОРА!!!)
ADMIN_IDS = [691555291]

@dp.message(Command("stats"))
async def command_stats(message: Message):
   if message.from_user.id not in ADMIN_IDS:
      await message.answer("У вас нет прав для просмотра этих данных.")
      return
      
   #Статистика пользователей
   total_users = 0
   total_tales = 0
   
   if Path(STATS_FILE).exists():		#Проверка сущестрования файла
      with open(STATS_FILE, 'r', newline = '', encoding='utf-8') as f:
         reader = csv.DictReader(f)	#DictReader исп-ет 1-ю строку ф-ла, как заголовки столбцов
         for row in reader:		#Пройти по каждой строке (каждому пользователю)
            total_users +=1		#Увели-е счетчика пользователей на 1 для каждой строки
            total_tales += int(row.get('tales_generated', 0))	#Добавле-е кол-ва сказок этого
            							# пользо-ля к общему счетчику
               
   #Статистика по сказкам
   age_stats = {}
   genre_stats = {}
   
   if Path(TALE_STATS_FILE).exists():
      with open(TALE_STATS_FILE, 'r', newline = '', encoding='utf-8') as f:
         reader = csv.DictReader(f)
         for row in reader:
            age = row.get('age_group', 'N/A')
            genre = row.get('genre', 'N/A')
            age_stats[age] = age_stats.get(age, 0) + 1
            genre_stats[genre] = genre_stats.get(genre, 0) + 1
               
   #Формируем отчет
   report = f"""
📊 Статистика бота:\n
👥 Всего пользователей: {total_users}
📖 Всего сгенерировано сказок: {total_tales}
\nВозрастные группы:\n"""
   for age_key in sorted(age_stats.keys()):
      count = age_stats[age_key]
      age_name = AGE_GROUP_NAMES.get(age_key)
      report += f" • {age_name}: {count}\n"
   report += "\nПопулярные жанры:\n"
   for genre, count in list(sorted(genre_stats.items(),
   key = lambda x: x[1], reverse = True))[:5]:
      report += f" • {genre}: {count}\n"
      
   await message.answer(report)
      
      
'''Клавиатуры для разных шагов'''
def get_age_keyboard():							#Кнопки для выбора возраста
   buttons = [[KeyboardButton(text ="1-2 года"),
   	     KeyboardButton(text = "3-5 лет")],
   	     [KeyboardButton(text = "6-8 лет")]]
   return ReplyKeyboardMarkup(keyboard = buttons, resize_keyboard = True)

def get_genre_keyboard():						#Кнопки для выбора жанра
   buttons = [[KeyboardButton(text ="волшебная сказка"),
   	     KeyboardButton(text = "сказка о животных")],
   	     [KeyboardButton(text ="бытовая сказка"),
   	     KeyboardButton(text = "сказка-притча")],
   	     [KeyboardButton(text ="страшная/готическая"),
   	     KeyboardButton(text = "приключения")],
   	     [KeyboardButton(text ="детектив"),
   	     KeyboardButton(text = "комедия")],
   	     [KeyboardButton(text ="драма"),
   	     KeyboardButton(text = "поучительная история")],
   	     [KeyboardButton(text ="фантастика"),
   	     KeyboardButton(text = "психологическая")],]
   return ReplyKeyboardMarkup(keyboard = buttons, resize_keyboard = True)

def get_style_keyboard():						#Кнопки для выбора стиля
   buttons = [[KeyboardButton(text ="народный/фольклорный"),
   	     KeyboardButton(text = "лирический/поэтический")],
   	     [KeyboardButton(text ="таинственный/загадочный"),
   	     KeyboardButton(text = "уютный")],
   	     [KeyboardButton(text ="юмористический"),
   	     KeyboardButton(text = "приключенческий")],
   	     [KeyboardButton(text ="эпический/героический"),
   	     KeyboardButton(text = "темный/готический")],
   	     [KeyboardButton(text ="восточный"),
   	     KeyboardButton(text = "скандинавский")]]
   return ReplyKeyboardMarkup(keyboard = buttons, resize_keyboard = True)

init_stats_files()		#Инициализация файлов статистики при запуске

def get_gender_keyboard():						#Кнопки для выбора пола ребенка
   buttons = [[KeyboardButton(text ="мальчик"),
   	     KeyboardButton(text = "девочка")]]
   return ReplyKeyboardMarkup(keyboard = buttons, resize_keyboard = True)

def get_audio_keyboard():						#Кнопки для выбора озвучки
   buttons = [[KeyboardButton(text ="Да, хочу озвучить сказку"),
   	     KeyboardButton(text = "Нет, мне нужен только текст")]]
   return ReplyKeyboardMarkup(keyboard = buttons, resize_keyboard = True)
   
def get_voice_keyboard():						#Кнопки для выбора голоса
   buttons = [[KeyboardButton(text ="Женский голос"),
   	     KeyboardButton(text = "Мужской голос")]]
   return ReplyKeyboardMarkup(keyboard = buttons, resize_keyboard = True)


'''начало работы и ввода данных'''
@dp.message(Command("start"))
async def command_start(message:Message):
#Сброс данных пользователя при каждом новом старте
   user_data[message.from_user.id] = {"step": "age"}
   
   update_user_stats(message.from_user)	#Обновляем статистику пользователя при запуске

   await message.answer("<b><i>Привет, дорогой друг!</i></b>\n\nЯ твой персональный сочинитель сказок 📚," 
   		" создам сказку по твоему предпочтению 🫶.\n\n"
		"Для какого возраста будем писать? ✍️", 
		reply_markup = get_age_keyboard())
		
@dp.message()
async def process_inform(message:Message):
   user_id = message.from_user.id
#Если пользователь только начал, предлагаем начать с команды /start
   if user_id not in user_data:
      await message.answer("Напишите <b>/start</b>, чтобы начать создание сказки.",
      reply_markup = ReplyKeyboardRemove())
      return
   current_step = user_data[user_id].get("step")
   
   #Обрабатываем выбор возраста
   if current_step == "age":
      age_mapping = {"1-2 года":"1",
   		     "3-5 лет":"2",
   		     "6-8 лет":"3"}
      if message.text in age_mapping:
         user_data[user_id] = {"age": age_mapping[message.text], "step": "genre"}
         await message.answer("<b><i>Отлично! Начало положено!</i></b>\n\n"
         		      "Выбери жанр авторской сказки "
          		      "или напиши свой вариант (например: героическая история)",
          		      reply_markup = get_genre_keyboard())
      else: await message.answer("Пожалуйста выбери возраст из предложенных вариантов",
      				reply_markup = get_age_keyboard())

   #Обрабатываем выбор жанра
   elif current_step == "genre":
      user_data[user_id]["genre"] = message.text
      user_data[user_id]["step"] = "style"
      await message.answer("<b><i>Укажи в каком стиле будем писать сказку</i></b>🧸:\n\n"
      			   
      			   "Или можешь придумать свой вариант 🤗",
      			   reply_markup = get_style_keyboard())
   
   #Обрабатываем выбор стиля
   elif current_step == "style":
      user_data[user_id]["style"] = message.text
      user_data[user_id]["step"] = "location"
      await message.answer("<b><i>Где будет происходить действие?</i></b> 🗺️\n\n"
      			 "Например:\n"
      			 "• сказочный лес\n• другая планета\n• дно океана\n"
      			 "• пещера дружелюбного тролля и так далее...\n\n"
      			 "<i>Придумай оригинальную локацию 🏔️🏕️🏝️ или напиши"
      			 " мне: <b>придумай сам</b></i>, я все сделаю", 
      			 reply_markup = ReplyKeyboardRemove())
   
   #Обрабатываем место действия
   elif current_step == "location":
      user_data[user_id]["location"] = message.text
      user_data[user_id]["step"] = "hero"
      await message.answer("<b><i>Придумай имя главного героя</i></b> 🦸‍♂️\n\n"
      			   "Например:\n"
      			   "• котенок-плутишка\n• принцесса, которая не верила в магию\n"
      			   "• вечно смеющийся мышонок\n• девочка Катя и так далее...")
	
   #Обрабативаем имя героя
   elif current_step == "hero":
      user_data[user_id]["hero"] = message.text
      user_data[user_id]["step"] = "enemy"
      await message.answer("<b><i>Теперь пора придумать злодея\n" 
      			   "с кем наш герой будет бороться\n"
      			   "или препятствие, которое он будет преодолевать. 🌋</i></b>\n\n"
      			   "Например: 'Дракон-лентяй' или 'высохшая река.'\n\n"
      			   "Если хочешь, чтобы это сделал я, напиши: <b><i>придумай сам</i></b>")
   
   #Обрабатываем злодея/проблему
   elif current_step == "enemy":
      user_data[user_id]["enemy"] = message.text
      user_data[user_id]["step"] = "child_name"
      await message.answer("<b><i>Как зовут ребенка, для которого пишем сказку? 👶</i></b>")	
	
   #Обрабатываем имя ребенка
   elif current_step == "child_name":
      user_data[user_id]["child_name"] = message.text
      user_data[user_id]["step"] = "gender"
      await message.answer("<b><i>Укажи пол ребенка 👦👧</i></b>", 
      reply_markup = get_gender_keyboard())
  
   #Обрабатываем пол ребенка
   elif current_step == "gender":
      if message.text in ["мальчик", "девочка"]:
         user_data[user_id]["gender"] = message.text
         user_data[user_id]["step"] = "audio_choice"
         await message.answer("<b><i>Отлично! Все данные собраны.\n🔮Генерирую сказку🔮</i></b>", 
            reply_markup=ReplyKeyboardRemove())
        
         #Генерируем сказку
         story = await generate_story(user_data[user_id])
         user_data[user_id]["generated_story"] = story		#Сохраняем сказку
         
         #Отправляем текстовую версию и предлагаем озвучку
         await message.answer(story)				#Отправляем текстовую версию сказки
         await message.answer("🎧 <b>Хочешь получить озвученную версию этой сказки?</b>",
            reply_markup = get_audio_keyboard()) 
         
      else: 
         await message.answer("Пожалуйста выбери пол ребенка из предложенных вариантов", 
                          reply_markup=get_gender_keyboard())
   
   #Обрабатываем выбор озвучки
   elif current_step == "audio_choice":
      if message.text == "Да, хочу озвучить сказку":
         #Выбираем голос
         user_data[user_id]["step"] = "voice_choice"
         await message.answer("<b><i>Выбери голос для озвучки сказки </i></b>🎙",
            reply_markup=get_voice_keyboard())
      
      elif message.text == "Нет, мне нужен только текст":
         await message.answer("<b><i>Хорошего чтения! Если захочешь, новую сказку - напиши /start</i></b>",
            reply_markup=ReplyKeyboardRemove())
                 
         #Логируем и очищаем данные
         log_tale_generation(user_id, user_data[user_id])
         del user_data[user_id]
      else:
         await message.answer("<b><i>Пожалуйста, выбери один из вариантов</i></b>",
            reply_markup=get_audio_keyboard())
   
   #Обрабатываем выбор голоса
   elif current_step == "voice_choice":
      if message.text in ["Женский голос", "Мужской голос"]:
         #Определяем тип голоса
         voice_type = "женский" if "Женский" in message.text else "мужской"
         user_data[user_id]["voice_type"] = voice_type
         user_data[user_id]["audio_requested"] = True
         await message.answer(f"🎧 <b><i>Создаю аудиоверсию сказки({voice_type} голос)...</i></b>",
         reply_markup=ReplyKeyboardRemove())
   
         try:
            #Получаем сохраненную сказку
            story_text = user_data[user_id].get("generated_story", "")
            
            #Проверяем инициализацию TTS менеджера
            if not tts_manager:
               await message.answer("⚠️ <b><i>Сервис озвучки временно недоступен. Попробуйте позже.</i></b>")
               
               #Логируем и очищаем данные
               log_tale_generation(user_id, user_data[user_id])
               del user_data[user_id]
               return
            
            if story_text:
               #Генерируем аудио с выбором голоса
               audio_file = await tts_manager_instance.text_to_speech(text = story_text.strip(),
               						     voice_type = voice_type,
               						     emotion = "good")
               #Создаем название аудиофайла
               hero_name = user_data[user_id].get('hero', 'сказка').replace(' ', '_')[:20]	#Ограничиваем длину
               filename = f"{hero_name}_сказка.mp3"
               
               #Читаем данные из BytesIO
               audio_data = audio_file.getvalue()
               
               #Проверяем размер файла: Telegram ограничивает 50MB)
               if len(audio_data) > 50 * 1024 *1024:
                  await message.answer("⚠️ <b><i>Аудиофайл слишком большой для отправки</i></b>")
               
               else:
                  #Отправляем аудио с обработкой ошибок
                  try:
                     await message.answer_audio(audio = types.BufferedInputFile(audio_data,
               								  filename = filename),
               								  title = f"Сказка про {user_data[user_id].get('hero', 'героя')}",
               								  performer = "Генератор сказок",
               								  caption = f"Аудиоверсия ({voice_type} голос)")
                     await message.answer("✅ <b><i>Аудиоверсия готова! Приятного прослушивания!</i></b>")
         
                  except Exception as send_error:
                     print(f"Audio sending error: {send_error}")
                     await message.answer("⚠️ <b><i>Ошибка при отправке аудио. Попробуйте позже.</i></b>!")      
            else:
               await message.answer("⚠️ <b><i>Текст сказки не найден</i></b>!")
         except Exception as e:
            print(f"Audio generation error: {e}")
            await message.answer("⚠️ <b><i>Произошла ошибка при создании аудиоверсии</i></b>!")
            
         #Логируем генерацию сказки в csv файл
         log_tale_generation(user_id, user_data[user_id])
        
         #Очищаем данные пользователя после генерации
         del user_data[user_id]   
      else:
         await message.answer("<b><i>Пожалуйста, выбери тип голоса</i></b> 🗣",
            reply_markup = get_voice_keyboard())
         return						#Не очищаем данные, если выбор неправильный


'''Генерация сказки'''
async def generate_story(data):
   age_mapping = { "1":"1-2 года",
   		   "2":"3-5 лет",
   		   "3":"6-8 лет"}
   		   
   #Определяем специфические требивания для разных возрастных групп
   age_specific_instructions = {"1":"""Для возраста 1-2 года создай очень простую сказку в стиле 'Колобок', 'Курочка Ряба', 'Репка' и других похожих русских сказок.
   Особые требования:
   - Простой сюжет с минимумом персонажей
   - Яркие, понятные образы
   - Обязательный happy end
   - Добавь элементы, которые можно повторять 
   (как 'я от дедушки ушел' в Колобке и так далее)
   - Длина сказки 1500 символов. Обязательно соблюдай эту длину!""",
   				
"2":"""Для возраста 3-5 лет:
   - Простые, но более развернутые предложения
   - Четкий сюжет с завязкой, развитием и развязкой
   - Яркие персонажи с понятными характеристиками
   - Добрый юмор
   - Длина сказки 2500 символов. Обязательно соблюдай эту длину!""",
   				
"3":"""Для возраста 6-8 лет:
   - Более сложный сюжет с неожиданными поворотами
   - Развернутые описания персонажей и мест
   - Может содержать элементы напряжения и их разрешения
   - Поучительный компонент
   - Длина сказки 3500 символов. Обязательно соблюдай эту длину!"""}
   age_instruction = age_specific_instructions.get(data['age'],"")
   		  
   promt = f"""
Создай детскую сказку на русском языке, идеально подходящую для ребенка 
{age_mapping.get(data['age'], data['age'])}.
{age_instruction} 
Жанр -  {data.get('genre', 'добрый')}.
Стиль сказки - {data.get('style', 'приключения')}.
Место действия - {data.get('location', 'сказочный лес')}.
Главный герой - {data.get('hero', 'добрый медвежонок')}.
Противник или проблема - {data.get('enemy', 'страшный лев')}.
Вставь имя ребенка {data.get('child_name', 'малыш')} в историю.
Пол ребенка - {data.get('gender')}.
Сказка должна быть поучительной, доброй и интересной.
В заголовке укажи название сказки.
ВАЖНО: длина сказки не должна превышать 4000 символов!
ВАЖНО: 
- Используй только кириллицу (русские буквы)!
- Выводи только название и саму сказку бездополнительных комментариев!
- Не упоминать политические темы, конфликты, войны.
- Не упоминать Украину, лидера Зеленского и все что с нини связано.
- Не затрагивать межнациональные конфликты.
- Не должно быть сцен насилия, страшных описаний, негативных эмоций.
- Не затрагивать религиозные темы.
- Не упоминать ад, преисподняя, дьявол, люцефер, демон, бес и любые склоняемые с ними слова.
- Сказка должна быть абсолютно аполитичной и безопасной для детей!"""
   
   print(promt)	
   
   #Запрос к API DeepSeek
   headers = {"Content-Type": "application/json",
   		"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}
   #Данные для запроса
   payload = {"model": "deepseek-chat",
   	      "messages": [{"role": "system",
   	      "content": "Ты детский писатель, специализирующийся на создании добрых поучительных сказок."},
   	      {"role": "user", "content": promt}],
   	      "temperature": 0.7,
   	      "max_tokens": 4000}
   	      
   #Отправка запроса к API
   async with aiohttp.ClientSession() as session:
      async with session.post(DEEPSEEK_API_URL, 
      headers = headers, json = payload) as response:
         if response.status == 200:
            result = await response.json()
            story = result["choices"][0]["message"]["content"]
            return story
        
         else:
            error_text = await response.text()
            print(f"Ошибка API:{response.status},{error_text}")
           
            #Возвращаем заглушку в случае ошибки 
            generated_story = f"""
   **Сказка про {data.get('hero', 'храброго героя')}**
   
   Жил был {data.get('hero', 'добрый медвежонок')}.
   Однажды случилась беда: 
   {data.get('enemy', 'страшный лев')} напал на деревню.
   
   Маленький {data.get('child_name', 'малыш')} решил помочь!
   Он собрал всех зверей вместе и победил злодея!
   
   **Мораль: дружба решает любые проблемы!"""
   
            return generated_story
#Инициализируем TTS менеджер при старте
tts_manager_instance = None
   
async def main():
   try:
      tts_manager_instance = init_tts_manager()			#Инициализация TTS менеджера (получаем экзепляр)
      if tts_manager_instance:
         print("✅ Yandex SpeechKit initialized successfully!")
      else:
         print("Yandex SpeechKit initialization failed - check API keys")
   except Exception as e:
      print(f"❌ SpeechKit initialization failed: {e}")
      
   print("Бот запущен!")
   await bot.delete_webhook(drop_pending_updates=True)
   await dp.start_polling(bot)
   
if __name__=="__main__":
   asyncio.run(main())

