import aiohttp			#Для асинхронных HTTP-запросов к API
import io			#Для работы с бинарными данными в памяти 
import os			#Для работы с переменными окружения

class YandexSpeechKit:
   def __init__(self, api_key, folder_id):
      self.api_key = api_key			#Ключ для доступа к API
      self.folder_id = folder_id		#ID  папки в Yandex Cloud
      self.api_url = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
      
      #Доступные голоса для русского языка
      self.available_voices = {"женский": {"voice": "oksana",
      					   "description": "Оксана - эмоциональный женский голос",
      					   "emotion": "good",
      					   "speed": "0.9"},
      			       "мужской": {"voice": "filipp",
      			       		   "description": "Филипп - глубокий мужской голос",
      			       		   "emotion": "good",
      					   "speed": "1.0"}}
   def ssml_pauses(self, text):
      #Добавляем паузы для более естественной речи
      text = text.replace('\n\n', '<break time="700ms"/>')
      text = text.replace('\n', '<break time="400ms"/>')
      text = text.replace('. ', '.<break time="600ms"/>')
      text = text.replace('! ', '!<break time="500ms"/>')
      text = text.replace('? ', '?<break time="500ms"/>')
      text = text.replace(', ', ',<break time="300ms"/>')
      text = text.replace(': ', ':<break time="300ms"/>')
      return f'<speak>{text}</speak>'
   async def text_to_speech(self, text: str, voice_type: str = "женский", 
   emotion: str = None) -> io.BytesIO:
      
      '''Преобразование текста в речь через Yandex SpeechKit
      voice_type: "женский" или "мужской"'''
      
      #Получаем конкретный голос из доступных
      voice_info = self.available_voices.get(voice_type, self.available_voices["женский"])
      voice = voice_info["voice"]
      
      #Получаем скорость и эмоцию из настроек голоса
      speed = voice_info.get("speed", "1.0")
      if emotion is None:
         emotion = voice_info.get("emotion", "good")
         
      #Подготавливаем текст
      prepared_text = self.ssml_pauses(text)
      
      headers = {"Authorization": f"Api-Key {self.api_key}",		#Авторизация по API-ключу
      		"Content-Type": "application/x-www-form-urlencoded"}	
      
      data = {"ssml": prepared_text,			#Текст озвучки
      	      "lang": "ru-RU",			#Язык - русский
      	      "voice": voice,			#Выбор голоса
      	      "emotion": emotion,		#Эмоциональная окраска (добрая, злая, нормальная)
      	      "speed": speed,			#Скорость речи (нормальная)
      	      "format": "mp3",			#Формат аудио
      	      "folderId": self.folder_id}	#Идентификатор облака

      print(f"TTS params: voice={voice}, emotion={emotion}, speed={speed}")
      
      try:
         async with aiohttp.ClientSession() as session:
            async with session.post(self.api_url, headers = headers, data = data) as response:
               if response.status == 200:
                  audio_data = await response.read()		#Если запрос успешен, то читаем аудио-данные
                  return io.BytesIO(audio_data)			#Создание файла в виртуальной памяти
               else:
                  error_text = await response.text()
                  print(f"SpeechKit error: {response.status}, {error_text}")
                  print(f"API Key: {self.api_key[:10]}...")
                  print(f"Folder ID: {self.folder_id}")
                  raise Exception (f"SpeechKit API error: {response.status}")
      except Exception as e:
         print(f"SpeechKit connection error: {e}")
         raise
#Глобальный экземпляр TTS менеджера
tts_manager = None

def init_tts_manager():
   global tts_manager
   api_key = os.getenv("YANDEX_TTS_API_KEY")
   folder_id = os.getenv("YANDEX_FOLDER_ID")
   print(f"API Key exists: {bool(api_key)}")		#Для отладки
   print(f"Folder ID exists: {bool(folder_id)}")	#Для отладки
   
   if api_key and folder_id:
      tts_manager = YandexSpeechKit(api_key, folder_id)
      print("Yandex SpeechKit initialized successfully!")
      return tts_manager
   else:
      print("Yandex TTS API keys not found - audio generation disabled")
   return None

#Функция для получения менеджера
def get_tts_manager():
   global tts_manager
   return tts_manager


