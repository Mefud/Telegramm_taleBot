import aiohttp			#Для асинхронных HTTP-запросов к API
import io			#Для работы с бинарными данными в памяти 
import os			#Для работы с переменными окружения

class YandexSpeechKit:
   def __init__(self, api_key, folder_id):
      self.api_key = api_key			#Ключ для доступа к API
      self.folder_id = folder_id		#ID  папки в Yandex Cloud
      self.api_url = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
      
      #Доступные голоса для русского языка
      self.available_voices = {"женский": {"voice": "alena",
      					   "description": "Алена - приятный женский голос"},
      			       "мужской": {"voice": "filipp",
      			       		   "description": "Филипп - глубокий мужской голос"}}
      
   async def text_to_speech(self, text: str, voice_type: str = "женский", 
   emotion: str = "good") -> io.BytesIO:
      
      '''Преобразование текста в речь через Yandex SpeechKit
      voice_type: "женский" или "мужской"'''
      
      #Получаем конкретный голос из доступных
      voice_info = self.available_voices.get(voice_type, self.available_voices ["женский"])
      voice = voice_info["voice"]
      
      headers = {"Authorization": f"Api-Key {self.api_key}"}	#Авторизация по API-ключу
      data = {"text": text,			#Текст озвучки
      	      "lang": "ru-RU",			#Язык - русский
      	      "voice": voice,			#Выбор голоса
      	      "emotion": emotion,		#Эмоциональная окраска (добрая, злая, нормальная)
      	      "speed": "1.0",			#Скорость речи (нормальная)
      	      "format": "mp3",			#Формат аудио
      	      "folderId": self.folder_id}	#Идентификатор облака
      
      try:
         async with aiohttp.ClientSession() as session:
            async with session.post(self.api_url, headers = headers, data = data, timeout=TIMEOUT ) as response:
               if response.status == 200:
                  audio_data = await response.read()		#Если запрос успешен, то читаем аудио-данные
                  return io.BytesIO(audio_data)			#Создание файла в виртуальной памяти
               else:
                  error_text = await response.text()
                  print(f"SpeechKit error: {response.status}, {error_text}")
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
   else:
      print("Yandex TTS API keys not found - audio generation disabled")
   return tts_manager


