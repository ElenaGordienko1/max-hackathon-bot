import asyncio
import json
import logging
import os
from datetime import datetime

from dotenv import load_dotenv
from maxapi import Bot, Dispatcher, F
from maxapi.filters.command import CommandStart, Command
from maxapi.types import BotStarted, MessageCreated

from database import init_db, save_interests, get_interests
from util import clean_expired_events
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from maxapi.types import CallbackButton

load_dotenv()
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("MAX_BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

EVENTS_FILE = "db_events.json"

DB_EVENTS = []
CREATING_EVENT_STATES = {}

CATEGORIES = {
    "1": "Спортивные мероприятия",
    "2": "Музыкальные мероприятия",
    "3": "Театр",
    "4": "Искусство и хобби",
}


# --- РАБОТА С ФАЙЛАМИ ДАННЫХ ---

def load_all_data():
    global DB_EVENTS
    if os.path.exists(EVENTS_FILE):
        try:
            with open(EVENTS_FILE, "r", encoding="utf-8") as f:
                DB_EVENTS = json.load(f)
        except Exception:
            DB_EVENTS = []
    else:
        DB_EVENTS = [
            {"category": "Спортивные мероприятия", "title": "🏆 Благотворительный футбольный матч", "time": "29.09.2026 09:00"},
            {"category": "Спортивные мероприятия", "title": "🚴 Велозаезд по набережной", "time": "05.07.2027 20:00"},
            {"category": "Музыкальные мероприятия", "title": "🎸 Рок-фестиваль под открытым небом", "time": "28.09.2026 15:00"},
            {"category": "Музыкальные мероприятия", "title": "🎹 Вечер классической музыки в филармонии", "time": "01.02.2027 09:00"},
            {"category": "Театр", "title": "Спектакль 'Гамлет' (Премьера)", "time": "28.09.2026 15:00"},
            {"category": "Искусство и хобби", "title": "Мастер-класс по акварельной живописи", "time": "30.09.2026 06:00"},
            {"category": "Спортивные мероприятия", "title": "🏆 Футбольный матч хакатона", "time": "28.10.2026 09:00"},
            {"category": "Театр", "title": "🎭 Спектакль 'Гамлет'", "time": "28.09.2026 23:59"},
        ]
        save_events_to_file()


def save_events_to_file():
    try:
        with open(EVENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(DB_EVENTS, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Ошибка записи ивентов: {e}")


# --- ХЕЛПЕРЫ ДЛЯ ID ---

def get_user_id(event) -> int:
    """ID пользователя — для записи в БД."""
    if hasattr(event, "from_user") and event.from_user:
        uid = getattr(event.from_user, "user_id", None)
        if uid:
            return int(uid)
    if hasattr(event, "message") and event.message:
        sender = getattr(event.message, "sender", None)
        if sender:
            uid = getattr(sender, "user_id", None)
            if uid:
                return int(uid)
    return 0


def get_chat_id(event) -> int:
    """ID чата — для отправки сообщений через bot.send_message."""
    if hasattr(event, "message") and event.message:
        recipient = getattr(event.message, "recipient", None)
        if recipient:
            cid = getattr(recipient, "chat_id", None)
            if cid:
                return int(cid)
    if hasattr(event, "chat") and event.chat:
        cid = getattr(event.chat, "chat_id", None)
        if cid:
            return int(cid)
    return get_user_id(event)


async def get_categories_menu(user_id: int) -> str:
    user_choices = await get_interests(user_id)
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
    text += "/refresh — Очистить прошедшие события и обновить\n"
    text += "/start — Вернуться в главное меню"
    return text

CATEGORY_PAYLOADS = {
    "cat_sport": "Спортивные мероприятия",
    "cat_music": "Музыкальные мероприятия",
    "cat_theater": "Театр",
    "cat_art": "Искусство и хобби",
}


async def build_categories_keyboard(user_id: int):
    """Клавиатура с категориями. Выбранные помечаются ✅."""
    user_choices = await get_interests(user_id)
    builder = InlineKeyboardBuilder()
    for payload, name in CATEGORY_PAYLOADS.items():
        text = f"✅ {name}" if name in user_choices else f"🔹 {name}"
        builder.row(CallbackButton(text=text, payload=payload))
    builder.row(CallbackButton(text="Готово", payload="cat_done"))
    return builder.as_markup()


def build_commands_keyboard():
    """Клавиатура с дополнительными командами."""
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="📅 Мероприятия", payload="cmd_events"),
        CallbackButton(text="➕ Добавить", payload="cmd_add"),
    )
    builder.row(
        CallbackButton(text="👤 Мои интересы", payload="cmd_my"),
        CallbackButton(text="🔄 Обновить базу", payload="cmd_refresh"),
    )
    builder.row(CallbackButton(text="⚙️ Изменить интересы", payload="cmd_start"))
    return builder.as_markup()

# --- ОБРАБОТЧИКИ СОБЫТИЙ ---

@dp.bot_started()
async def handle_bot_started(event: BotStarted):
    user_id = get_user_id(event)
    chat_id = get_chat_id(event)
    await bot.send_message(
        chat_id=chat_id,
        text="Привет! Давай настроим твои интересы.\nВыбери категории:",
        attachments=[await build_categories_keyboard(user_id)],
    )


@dp.message_created(Command(commands=["refresh"]))
async def handle_refresh_events(event: MessageCreated):
    global DB_EVENTS
    deleted = clean_expired_events(EVENTS_FILE)
    try:
        with open(EVENTS_FILE, "r", encoding="utf-8") as f:
            DB_EVENTS = json.load(f)
    except Exception:
        DB_EVENTS = []
    if deleted > 0:
        await event.message.answer(
            text=f"База данных успешно обновлена!\nУдалено прошедших событий: {deleted}."
        )
    else:
        await event.message.answer(text="База данных обновлена! Прошедших событий не найдено.")


@dp.message_created(CommandStart())
async def handle_start_command(event: MessageCreated):
    user_id = get_user_id(event)
    CREATING_EVENT_STATES.pop(user_id, None)
    await event.message.answer(
        text="Выбери категории:",
        attachments=[await build_categories_keyboard(user_id)],
    )


@dp.message_created(Command(commands=["my"]))
async def handle_my_categories(event: MessageCreated):
    user_id = get_user_id(event)
    user_choices = await get_interests(user_id)
    if not user_choices:
        await event.message.answer(text="Вы еще не выбрали ни одной категории. Нажмите /start!")
    else:
        chosen_text = "\n".join([f"• {item}" for item in user_choices])
        await event.message.answer(
            text=f"Ваши сохраненные категории:\n\n{chosen_text}\n\nИзменить: /start"
        )


@dp.message_created(Command(commands=["events"]))
async def handle_get_events(event: MessageCreated):
    user_id = get_user_id(event)
    user_choices = await get_interests(user_id)

    if not user_choices:
        await event.message.answer(
            text="Вы не выбрали ни одной категории! Нажмите /start, чтобы настроить интересы."
        )
        return

    found_events = []
    for ev in DB_EVENTS:
        if ev["category"] in user_choices:
            found_events.append(
                f"🔹 {ev['title']}\n   Категория: {ev['category']}\n   Время: {ev['time']}\n"
            )

    if not found_events:
        await event.message.answer(
            text="К сожалению, по вашим категориям пока нет активных мероприятий."
        )
    else:
        result_text = (
            "Мероприятия под ваши интересы:\n\n"
            + "\n".join(found_events)
            + "\nИзменить настройки: /start"
        )
        await event.message.answer(text=result_text)


@dp.message_created(Command(commands=["add"]))
async def handle_add_event_start(event: MessageCreated):
    user_id = get_user_id(event)
    CREATING_EVENT_STATES[user_id] = {"step": "waiting_for_title"}
    await event.message.answer(
        text="Создание нового мероприятия\n\nВведите название вашего мероприятия:"
    )


@dp.message_created(F.message.body.text)
async def handle_any_text(event: MessageCreated):
    user_id = get_user_id(event)
    text = event.message.body.text.strip()

    # 1) Пользователь в процессе добавления мероприятия
    if user_id in CREATING_EVENT_STATES:
        state = CREATING_EVENT_STATES[user_id]

        if state["step"] == "waiting_for_title":
            state["title"] = text
            state["step"] = "waiting_for_category"

            menu_cat = "Выберите категорию для мероприятия:\n"
            for k, v in CATEGORIES.items():
                menu_cat += f"/{k} — {v}\n"
            await event.message.answer(
                text=f"Отлично! Название записано: {text}\n\n{menu_cat}"
            )
            return

        elif state["step"] == "waiting_for_category":
            clean_key = text.lstrip("/")
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
                await event.message.answer(
                    text="Пожалуйста, выберите категорию, нажав на одну из синих команд в меню."
                )
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
                "time": text,
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

    # 2) Обычная обработка команд-категорий
    clean_text = text.lstrip("/")
    if clean_text in CATEGORIES:
        category_name = CATEGORIES[clean_text]
        user_choices = await get_interests(user_id)

        if category_name in user_choices:
            user_choices.remove(category_name)
            status_msg = f"Вы удалили категорию: {category_name}\n\n"
        else:
            user_choices.append(category_name)
            status_msg = f"Вы добавили категорию: {category_name}\n\n"

        await save_interests(user_id, user_choices)
        await event.message.answer(
            text=status_msg,
            attachments=[await build_categories_keyboard(user_id)],
        )
    else:
        menu = await get_categories_menu(user_id)
        await event.message.answer(
            text="Неизвестная команда.",
            attachments=[build_commands_keyboard()],
        )


@dp.message_callback()
async def handle_callback(event):
    global DB_EVENTS

    # Достаём callback и payload
    if not hasattr(event, "callback") or not event.callback:
        return

    payload = getattr(event.callback, "payload", None)
    if not payload:
        return

    user_id = get_user_id(event)

    # --- ОБРАБОТКА КАТЕГОРИЙ (cat_) ---
    if payload.startswith("cat_"):
        # Кнопка «Готово»
        if payload == "cat_done":
            user_choices = await get_interests(user_id)
            if not user_choices:
                await event.answer(new_text="Ты ещё ничего не выбрал.")
                return
            chosen = ", ".join(user_choices)
            await event.answer(
                new_text=f"Отлично! Я запомнил, что тебе интересно: {chosen}.\n"
                         f"Теперь выбери, что делать дальше:",
                attachments=[build_commands_keyboard()],
            )
            return

        # Нажатие на категорию — добавить/удалить
        if payload not in CATEGORY_PAYLOADS:
            return

        category_name = CATEGORY_PAYLOADS[payload]
        user_choices = await get_interests(user_id)

        if category_name in user_choices:
            user_choices.remove(category_name)
        else:
            user_choices.append(category_name)

        await save_interests(user_id, user_choices)

        await event.answer(
            new_text="Отметь ещё или нажми «Готово».",
            attachments=[await build_categories_keyboard(user_id)],
        )
        return

    # --- ОБРАБОТКА КОМАНД (cmd_) ---
    if payload.startswith("cmd_"):
        if payload == "cmd_events":
            user_choices = await get_interests(user_id)
            if not user_choices:
                await event.answer(new_text="Вы не выбрали ни одной категории! Нажмите /start.")
                return
            found_events = []
            for ev in DB_EVENTS:
                if ev["category"] in user_choices:
                    found_events.append(
                        f"🔹 {ev['title']}\n   Категория: {ev['category']}\n   Время: {ev['time']}\n"
                    )
            if not found_events:
                await event.answer(new_text="К сожалению, по вашим категориям пока нет активных мероприятий.")
            else:
                result_text = "Мероприятия под ваши интересы:\n\n" + "\n".join(found_events)
                await event.answer(new_text=result_text)

        elif payload == "cmd_add":
            CREATING_EVENT_STATES[user_id] = {"step": "waiting_for_title"}
            await event.answer(new_text="Создание нового мероприятия\n\nВведите название вашего мероприятия:")

        elif payload == "cmd_my":
            user_choices = await get_interests(user_id)
            if not user_choices:
                await event.answer(new_text="Вы еще не выбрали ни одной категории. Нажмите /start!")
            else:
                chosen_text = "\n".join([f"• {item}" for item in user_choices])
                await event.answer(new_text=f"Ваши сохраненные категории:\n\n{chosen_text}")

        elif payload == "cmd_refresh":
            deleted = clean_expired_events(EVENTS_FILE)
            try:
                with open(EVENTS_FILE, "r", encoding="utf-8") as f:
                    DB_EVENTS = json.load(f)
            except Exception:
                DB_EVENTS = []
            if deleted > 0:
                await event.answer(new_text=f"База обновлена! Удалено событий: {deleted}.")
            else:
                await event.answer(new_text="База обновлена! Прошедших событий не найдено.")

        elif payload == "cmd_start":
            await event.answer(
                new_text="Выбери категории:",
                attachments=[await build_categories_keyboard(user_id)],
            )
        return


async def main():
    await init_db()
    load_all_data()
    print("Бот с динамическим добавлением ивентов запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())