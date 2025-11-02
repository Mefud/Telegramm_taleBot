import aiohttp			#Для асинхронных HTTP-запросов к API
import io			#Для работы с бинарными данными в памяти 
import os			#Для работы с переменными окружения
import re
import pymorphy2

class YandexSpeechKit:
   def __init__(self, api_key, folder_id):
      self.api_key = api_key			#Ключ для доступа к API
      self.folder_id = folder_id		#ID  папки в Yandex Cloud
      self.api_url = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"
      
      #Инициализация pymorphy2
      try:
         self.morph = pymorphy2.MorphAnalyzer()
         print("pymorphy2 inicialized successfully!")
      except Exception as e:
         print(f"pymorph2 inicialization failed: {e}")
         self.morph = None
      
      #Доступные голоса для русского языка
      self.available_voices = {"женский": {"voice": "oksana",
      					   "description": "Оксана - эмоциональный женский голос",
      					   "emotion": "good",
      					   "speed": "0.9"},
      			       "мужской": {"voice": "filipp",
      			       		   "description": "Филипп - глубокий мужской голос",
      			       		   "emotion": "good",
      					   "speed": "1.0"}}
      					   
      #Словарь эмоциональных слов
      self.emotional_words = {"радостный": {"rate": "fast", "pitch":"high"},
      			      "счастливый": {"rate": "fast", "pitch":"high"},
      			      "веселый": {"rate": "fast", "pitch":"high"},
      			      "ура": {"rate": "fast", "pitch":"high"},
      			      "победа": {"rate": "fast", "pitch":"high"},
      			      "ликовать": {"rate": "fast", "pitch":"high"},
      			      "торжествовать": {"rate": "fast", "pitch":"high"},
      			      
      			      "тихий": {"rate": "slow", "pitch":"low"},
      			      "шепот": {"rate": "slow", "pitch":"low"},
      			      "тайный": {"rate": "slow", "pitch":"low"},
      			      "осторожный": {"rate": "slow", "pitch":"low"},
      			      "страшный": {"rate": "slow", "pitch":"low"},
      			      "пугающий": {"rate": "slow", "pitch":"low"},
      			      "загадочный": {"rate": "slow", "pitch":"low"},
      			      
      			      "злой": {"rate": "medium", "pitch":"low", "volume": "loud"},
      			      "сердитый": {"rate": "medium", "pitch":"low", "volume": "loud"},
      			      "грозный": {"rate": "medium", "pitch":"low", "volume": "loud"},
      			      
      			      "добрый": {"rate": "medium", "pitch":"medium"},
      			      "ласковый": {"rate": "medium", "pitch":"medium"},
      			      "нежный": {"rate": "medium", "pitch":"medium"},}
      
   def ssml_pauses(self, text):
      #Добавляем паузы для более естественной речи
      text = text.replace('\n\n', '<break time="900ms"/>')
      text = text.replace('\n', '<break time="400ms"/>')
      text = text.replace('. ', '.<break time="600ms"/>')
      text = text.replace('! ', '!<break time="500ms"/>')
      text = text.replace('? ', '?<break time="500ms"/>')
      text = text.replace(', ', ',<break time="300ms"/>')
      text = text.replace(': ', ':<break time="300ms"/>')
      return f'<speak>{text}</speak>'
      
   def prepare_text_with_pymorphy(self, story_text):
      """Использование pymorphy2 для морфологического анализа"""
      if self.morph is None:
         #Если pymorphy2 не работает, используем упрощенную версию
         return self.ssml_pauses(story_text)
      
      def get_normal_form(word):
         """Получаем нормальную форму слова"""
         try:
            parsed = self.morph.parse(word)[0]
            return parsed.normal_form
         except:
            return word
            
      def find_emotional_words(sentence):
         """Находит эмоциональные слова с учетом падежей"""
         words = re.findall(r'\b[а-яё]+\b', sentence.lower())
         found_emotions = []
         for word in words:
            normal_form = get_normal_form(word)
            if normal_form in self.emotional_words:
               found_emotions.append(self.emotional_words[normal_form])
         return found_emotions
         
      #Разбиваем на предложения
      sentences = re.split(r'[.!?]+', story_text)
      sentences = [s.strip() for s in sentences if s.strip()]
      
      enhanced_sentences = []
      
      for sentence in sentences:
         if not sentence:
            continue
            
         emotional_settings = find_emotional_words(sentence)
         
         if emotional_settings:
            settings = emotional_settings[0]
            prosody_attrs = [f'{k}="{v}"' for k, v in settings.items()]
            prosody_str = ' '.join(prosody_attrs)
            enhanced_sentences.append(f'<prosody {prosody_str}>{sentence}</prosody>')
         else:
            enhanced_sentences.append(sentence)
            
      #Собираем текст обратно
      result = '. '.join(enhanced_sentences)
      
      #Добавляем SSML паузы
      result = result.replace('\n\n', '<break time="900ms"/>')
      result = result.replace('\n', '<break time="400ms"/>')
      result = result.replace('. ', '.<break time="600ms"/>')
      result = result.replace('! ', '!<break time="500ms"/>')
      result = result.replace('? ', '?<break time="500ms"/>')
      result = result.replace(', ', ',<break time="300ms"/>')
      result = result.replace(': ', ':<break time="300ms"/>')
      return f'<speak>{result}</speak>'      
        
   async def text_to_speech(self, text: str, voice_type: str = "женский", 
   emotion: str = None, use_enhanced_processing: bool = True) -> io.BytesIO:
      
      '''Преобразование текста в речь через Yandex SpeechKit
      voice_type: "женский" или "мужской"
      use_enhanced_processing: использовать улучшенную обработку текста'''
      
      #Получаем конкретный голос из доступных
      voice_info = self.available_voices.get(voice_type, self.available_voices["женский"])
      voice = voice_info["voice"]
      
      #Получаем скорость и эмоцию из настроек голоса
      speed = voice_info.get("speed", "1.0")
      if emotion is None:
         emotion = voice_info.get("emotion", "good")
         
      #Подготавливаем текст (простой или улучшенный вариант)
      if use_enhanced_processing and self.morph is not None:
         prepared_text = self.prepare_text_with_pymorphy(text)
         print("Using enhanced text processing with pymorphy2")
      else:
         prepared_text = self.ssml_pauses(text)
         print("Using basic text processing not pymorphy2")
      
      headers = {"Authorization": f"Api-Key {self.api_key}",		#Авторизация по API-ключу
      		"Content-Type": "application/x-www-form-urlencoded"}	
      
      data = {"ssml": prepared_text,		#Текст озвучки
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


