import asyncio
import json
import logging
import os

from maxapi import Bot, Dispatcher, F
from maxapi.filters.command import CommandStart, Command
from maxapi.types import BotStarted, MessageCreated
from dotenv import load_dotenv

load_dotenv()  
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("MAX_BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

DATA_FILE = "user_preferences.json"
USER_PREFERENCES = {}

# --- БАЗА ДАННЫХ МЕРОПРИЯТИЙ ДЛЯ ХАКАТОНА ---  времено потом что-то надо сделать
DB_EVENTS = [
    {"category": "Спортивные мероприятия", "title": "🏆 Благотворительный футбольный матч", "time": "Завтра в 12:00"},
    {"category": "Спортивные мероприятия", "title": "🚴 Велозаезд по набережной", "time": "Воскресенье в 09:00"},
    {"category": "Музыкальные мероприятия", "title": "🎸 Рок-фестиваль под открытым небом", "time": "Суббота в 19:00"},
    {"category": "Музыкальные мероприятия", "title": "🎹 Вечер классической музыки в филармонии", "time": "Пятница в 18:30"},
    {"category": "Театр", "title": " Спектакль 'Гамлет' (Премьера)", "time": "Суббота в 18:00"},
    {"category": "Искусство и хобби", "title": " Мастер-класс по акварельной живописи", "time": "Воскресенье в 15:00"}
]

# --- РАБОТА С ФАЙЛОМ ---
def load_data_from_file():
    global USER_PREFERENCES
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                USER_PREFERENCES = json.load(f)
            print("Данные пользователей успешно загружены из файла!")
        except Exception as e:
            print(f"Ошибка при чтении файла данных: {e}")
            USER_PREFERENCES = {}
    else:
        USER_PREFERENCES = {}

def save_data_to_file():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(USER_PREFERENCES, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Ошибка при записи данных в файл: {e}")

CATEGORIES = {
    "1": "Спортивные мероприятия",
    "2": "Музыкальные мероприятия",
    "3": "Театр",
    "4": "Искусство и хобби"
}

def get_chat_id(event):
    if hasattr(event, 'data') and isinstance(event.data, dict):
        uid = event.data.get('chat_id') or event.data.get('user_id')
        return str(uid) if uid else None
    if hasattr(event, 'chat_id'):
        return str(event.chat_id)
    if hasattr(event, 'message') and hasattr(event.message, 'chat_id'):
        return str(event.message.chat_id)
    return None

#  МЕНЮ
def get_categories_menu(user_id):
    user_choices = USER_PREFERENCES.get(user_id, [])
    
    text = "Выберите категории мероприятий, подходящие вам:\n"
    text += "(Нажмите на синюю команду-цифру, чтобы добавить или удалить её)\n\n"
    
    for key, name in CATEGORIES.items():
        if name in user_choices:
            text += f"✅ /{key} — {name} (Выбрано)\n"  
        else:
            text += f"🔹 /{key} — {name}\n"
            
    text += "\nДополнительные команды:\n"
    text += "/events — Посмотреть подходящие мероприятия\n"
    text += "/my — Посмотреть мои выбранные категории\n"
    text += "/start — Вернуться в главное меню"
    return text

# ОБРАБОТЧИКИ СОБЫТИЙ

@dp.bot_started()
async def handle_bot_started(event: BotStarted):
    user_id = get_chat_id(event)
    await bot.send_message(
        chat_id=user_id, 
        text=f"Привет! Давай настроим твои интересы.\n\n{get_categories_menu(user_id)}"
    )

@dp.message_created(CommandStart())
async def handle_start_command(event: MessageCreated):
    user_id = get_chat_id(event)
    await event.message.answer(text=get_categories_menu(user_id))

@dp.message_created(Command(commands=["my"]))
async def handle_my_categories(event: MessageCreated):
    user_id = get_chat_id(event)
    user_choices = USER_PREFERENCES.get(user_id, [])
    
    if not user_choices:
        await event.message.answer(
            text="Вы еще не выбрали ни одной категории. Нажмите /start, чтобы сделать выбор!"
        )
    else:
        chosen_text = "\n".join([f"• {item}" for item in user_choices])
        await event.message.answer(
            text=f"Ваши сохраненные категории:\n\n{chosen_text}\n\nВы можете изменить их в любое время через /start"
        )

# вывод персональных мероприятий по команде /events
@dp.message_created(Command(commands=["events"]))
async def handle_get_events(event: MessageCreated):
    user_id = get_chat_id(event)
    user_choices = USER_PREFERENCES.get(user_id, [])
    
    if not user_choices:
        await event.message.answer(
            text="Вы не выбрали ни одной категории! Нажмите /start, чтобы настроить свои интересы."
        )
        return
        
    found_events = []
    for ev in DB_EVENTS:
        if ev["category"] in user_choices:
            found_events.append(f"🔹 **{ev['title']}**\n   Категория: {ev['category']}\n   Время: {ev['time']}\n")
            
    if not found_events:
        await event.message.answer(text="К сожалению, по вашим категориям пока нет активных мероприятий.")
    else:
        result_text = "Мероприятия, подобранные специально под ваши интересы:\n\n"
        result_text += "\n".join(found_events)
        result_text += "\nИзменить настройки: /start"
        await event.message.answer(text=result_text)

# удаляет пробелы и слэши
@dp.message_created(F.message.body.text.strip().lstrip('/').strip().in_(CATEGORIES.keys()))
async def handle_category_selection(event: MessageCreated):
    user_id = get_chat_id(event)
    
    selected_key = event.message.body.text.strip().lstrip('/').strip()
    category_name = CATEGORIES[selected_key]
    
    if user_id not in USER_PREFERENCES:
        USER_PREFERENCES[user_id] = []
        
    if category_name in USER_PREFERENCES[user_id]:
        USER_PREFERENCES[user_id].remove(category_name)
        status_msg = f"Вы удалили категорию: {category_name}\n\n"
    else:
        USER_PREFERENCES[user_id].append(category_name)
        status_msg = f"Вы добавили категорию: {category_name}\n\n"
        
    save_data_to_file()
    await event.message.answer(text=status_msg + get_categories_menu(user_id))

@dp.message_created(F.message.body.text)
async def handle_any_text(event: MessageCreated):
    user_id = get_chat_id(event)
    await event.message.answer(
        text=f"Неизвестная команда. Пожалуйста, используйте ссылки из меню:\n\n{get_categories_menu(user_id)}"
    )
@dp.message_created(F.message.body.text)
async def handle_any_text(event: MessageCreated):
    await event.message.answer(event.message.body.text)

async def main():
    load_data_from_file()
    print("Бот успешно запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
