import asyncio
import logging
import os

from maxapi import Bot, Dispatcher, F
from maxapi.filters.command import CommandStart
from maxapi.types import BotStarted, MessageCreated
from dotenv import load_dotenv

load_dotenv()  
logging.basicConfig(level=logging.INFO)


BOT_TOKEN = os.getenv("MAX_BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ОБРАБОТЧИКИ СОБЫТИЙ

@dp.bot_started()
async def handle_bot_started(event: BotStarted):
    await bot.send_message(
        chat_id=event.chat_id, 
        text="Привет! Я бот для хакатона. Напиши /start, чтобы поздороваться!"
    )

@dp.message_created(CommandStart())
async def handle_start_command(event: MessageCreated):
    await event.message.answer("Привет! Рад тебя видеть! Как дела?")

@dp.message_created(F.message.body.text)
async def handle_any_text(event: MessageCreated):
    await event.message.answer(event.message.body.text)

async def main():
    print("Бот запущен и слушает сообщения...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())