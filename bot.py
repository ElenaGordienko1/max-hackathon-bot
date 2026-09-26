import asyncio
import json
import logging
import os

from datetime import datetime
from maxapi import Bot, Dispatcher, F
from maxapi.filters.command import CommandStart, Command
from maxapi.types import BotStarted, MessageCreated
from dotenv import load_dotenv

load_dotenv()  
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("MAX_BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

PREFS_FILE = "user_preferences.json"
EVENTS_FILE = "db_events.json"

USER_PREFERENCES = {}
DB_EVENTS = []

CREATING_EVENT_STATES = {}

CATEGORIES = {
    "1": "Спортивные мероприятия",
    "2": "Музыкальные мероприятия",
    "3": "Театр",
    "4": "Искусство и хобби"
}

# --- РАБОТА С ФАЙЛАМИ ДАННЫХ ---
def load_all_data():
    global USER_PREFERENCES, DB_EVENTS
    if os.path.exists(PREFS_FILE):
        try:
            with open(PREFS_FILE, "r", encoding="utf-8") as f:
                USER_PREFERENCES = json.load(f)
        except Exception:
            USER_PREFERENCES = {}
    
    if os.path.exists(EVENTS_FILE):
        try:
            with open(EVENTS_FILE, "r", encoding="utf-8") as f:
                DB_EVENTS = json.load(f)
        except Exception:
            DB_EVENTS = []
    else:
        DB_EVENTS = [ #ПОТОМ ПОМЕНЯТЬ НА ДРУГИЕ НА РЕАЛЬНЫЕ ДАННЫЕ
            {"category": "Спортивные мероприятия", "title": "🏆 Благотворительный футбольный матч", "time": "29.09.2026 09:00"},
            {"category": "Спортивные мероприятия", "title": "🚴 Велозаезд по набережной", "time": "05.07.2027 20:00"},
            {"category": "Музыкальные мероприятия", "title": "🎸 Рок-фестиваль под открытым небом", "time": "28.09.2026 15:00"},
            {"category": "Музыкальные мероприятия", "title": "🎹 Вечер классической музыки в филармонии", "time": "01.02.2027 09:00"},
            {"category": "Театр", "title": "Спектакль 'Гамлет' (Премьера)", "time": "28.09.2026 15:00"},
            {"category": "Искусство и хобби", "title": "Мастер-класс по акварельной живописи", "time": "30.09.2026 06:00"},
            {"category": "Спортивные мероприятия", "title": "🏆 Футбольный матч хакатона", "time": "28.10.2026 09:00"},
            {"category": "Театр", "title": "🎭 Спектакль 'Гамлет'", "time": "28.09.2026 23:59"}
        ]
        save_events_to_file()

def save_prefs_to_file():
    try:
        with open(PREFS_FILE, "w", encoding="utf-8") as f:
            json.dump(USER_PREFERENCES, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Ошибка записи настроек: {e}")

def save_events_to_file():
    try:
        with open(EVENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(DB_EVENTS, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Ошибка записи ивентов: {e}")

def get_chat_id(event):
    for attr in ['chat_id', 'user_id', 'from_user_id']:
        if hasattr(event, attr) and getattr(event, attr):
            return str(getattr(event, attr))
    if hasattr(event, 'message') and event.message:
        for attr in ['chat_id', 'user_id', 'from_user_id']:
            if hasattr(event.message, attr) and getattr(event.message, attr):
                return str(getattr(event.message, attr))
    return "user_debug_id"  

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
    text += "/add — Добавить свое мероприятие\n"
    text += "/my — Посмотреть мои выбранные категории\n"
    text += "/start — Вернуться в главное меню"
    return text

# --- ОБРАБОТЧИКИ СОБЫТИЙ ---

@dp.bot_started()
async def handle_bot_started(event: BotStarted):
    user_id = get_chat_id(event)
    await bot.send_message(chat_id=user_id, text=f"Привет! Давай настроим твои интересы.\n\n{get_categories_menu(user_id)}")

@dp.message_created(CommandStart())
async def handle_start_command(event: MessageCreated):
    user_id = get_chat_id(event)
    CREATING_EVENT_STATES.pop(user_id, None)  
    await event.message.answer(text=get_categories_menu(user_id))

@dp.message_created(Command(commands=["my"]))
async def handle_my_categories(event: MessageCreated):
    user_id = get_chat_id(event)
    user_choices = USER_PREFERENCES.get(user_id, [])
    if not user_choices:
        await event.message.answer(text="Вы еще не выбрали ни одной категории. Нажмите /start!")
    else:
        chosen_text = "\n".join([f"• {item}" for item in user_choices])
        await event.message.answer(text=f"Ваши сохраненные категории:\n\n{chosen_text}\n\nИзменить: /start")

@dp.message_created(Command(commands=["events"]))
async def handle_get_events(event: MessageCreated):
    user_id = get_chat_id(event)
    user_choices = USER_PREFERENCES.get(user_id, [])
    
    if not user_choices:
        await event.message.answer(text="Вы не выбрали ни одной категории! Нажмите /start, чтобы настроить интересы.")
        return
        
    found_events = []
    for ev in DB_EVENTS:
        if ev["category"] in user_choices:
            found_events.append(f"🔹 {ev['title']}\n   Категория: {ev['category']}\n   Время: {ev['time']}\n")
            
    if not found_events:
        await event.message.answer(text="К сожалению, по вашим категориям пока нет активных мероприятий.")
    else:
        result_text = "Мероприятия под ваши интересы:\n\n" + "\n".join(found_events) + "\nИзменить настройки: /start"
        await event.message.answer(text=result_text)

@dp.message_created(Command(commands=["add"]))
async def handle_add_event_start(event: MessageCreated):
    user_id = get_chat_id(event)
    CREATING_EVENT_STATES[user_id] = {"step": "waiting_for_title"}
    await event.message.answer(text="Создание нового мероприятия\n\nВведите название вашего мероприятия:")

@dp.message_created(F.message.body.text)
async def handle_any_text(event: MessageCreated):
    user_id = get_chat_id(event)
    text = event.message.body.text.strip()
    if user_id in CREATING_EVENT_STATES:
        state = CREATING_EVENT_STATES[user_id]
        
        if state["step"] == "waiting_for_title":
            state["title"] = text
            state["step"] = "waiting_for_category"
            
            menu_cat = "Выберите категорию для мероприятия:\n"
            for k, v in CATEGORIES.items():
                menu_cat += f"/{k} — {v}\n"
            await event.message.answer(text=f"Отлично! Название записано: {text}\n\n{menu_cat}")
            return
            
        elif state["step"] == "waiting_for_category":
            clean_key = text.lstrip('/')
            if clean_key in CATEGORIES:
                state["category"] = CATEGORIES[clean_key]
                state["step"] = "waiting_for_time"
                await event.message.answer(
                    text=(
                        f"Категория выбрана: {state['category']}\n\n"
                        "Введите дату и время проведения в формате `ДД.ММ.ГГГГ ЧЧ:ММ`.\n"
                        "Пример: `28.09.2026 23:00`"
                    )
                )
            else:
                await event.message.answer(text="Пожалуйста, выберите категорию, нажав на одну из синих команд в меню.")
            return
            
        elif state["step"] == "waiting_for_time":
            try:
                input_date = datetime.strptime(text, "%d.%m.%Y %H:%M")
                current_date = datetime.now()
                if input_date < current_date:
                    await event.message.answer(
                        text="Ошибка: Вы ввели прошедшую дату! Мероприятие должно проходить в будущем. Попробуйте еще раз:"
                    )
                    return
            except ValueError:
                await event.message.answer(
                    text=(
                        "Неверный формат даты!\n"
                        "Пожалуйста, введите дату строго по шаблону `ДД.ММ.ГГГГ ЧЧ:ММ`.\n"
                        "Пример: `28.09.2026 23:00`"
                    )
                )
                return
                
            new_event = {
                "category": state["category"],
                "title": state["title"],
                "time": text  
            }
            DB_EVENTS.append(new_event)
            save_events_to_file()
            CREATING_EVENT_STATES.pop(user_id, None)  
            
            await event.message.answer(
                text=(
                    f"Мероприятие успешно добавлено!\n\n"
                    f"🔹 {new_event['title']}\n"
                    f"Категория: {new_event['category']}\n"
                    f"Время: {new_event['time']}\n\n"
                    "Оно уже доступно всем пользователям через команду /events !"
                )
            )
            return
    clean_text = text.lstrip('/')
    if clean_text in CATEGORIES:
        category_name = CATEGORIES[clean_text]
        if user_id not in USER_PREFERENCES:
            USER_PREFERENCES[user_id] = []
            
        if category_name in USER_PREFERENCES[user_id]:
            USER_PREFERENCES[user_id].remove(category_name)
            status_msg = f"Вы удалили категорию: {category_name}\n\n"
        else:
            USER_PREFERENCES[user_id].append(category_name)
            status_msg = f"Вы добавили категорию: {category_name}\n\n"
    await event.message.answer(text=f"Неизвестная команда.\n\n{get_categories_menu(user_id)}")
async def main():
    load_all_data()
    print("Бот с динамическим добавлением ивентов запущен...")
    await dp.start_polling(bot)
if __name__ == "__main__":
    asyncio.run(main())
            
