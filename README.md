# MAX Hackathon Bot 

Простой чат-бот для мессенджера **MAX**, написанный на Python. Создан в рамках хакатона. Умеет здороваться с пользователем, отвечать на команду `/start` и повторять введённый текст (эхо).

## Технологии

- **Python 3.10+**
- [**maxapi**](https://github.com/love-apples/maxapi) — асинхронная библиотека для MAX Bot API
- [**python-dotenv**](https://github.com/theskumar/python-dotenv) — загрузка переменных окружения из `.env`

## 📁 Структура проекта

```
max-bot/
├── bot.py              # основной код бота
├── requirements.txt    # зависимости
├── .env.example        # шаблон переменных окружения
├── .gitignore          # что не коммитить (venv, .env и т.д.)
└── README.md
```

## Установка и запуск

### 1. Клонировать репозиторий

```bash
git clone https://github.com/ElenaGordienko1/max-hackathon-bot.git
cd max-hackathon-bot
```

### 2. Создать виртуальное окружение

**Windows (PowerShell):**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Если PowerShell блокирует запуск скриптов:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**macOS / Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Установить зависимости

```bash
pip install -r requirements.txt
```

### 4. Настроить токен

Скопируйте `.env.example` в `.env` 

Откройте `.env` и впишите свой токен:

```
MAX_BOT_TOKEN=ваш_реальный_токен_здесь
```

> ⚠️ **Важно:** файл `.env` добавлен в `.gitignore` и не попадает в репозиторий. !!!Реальный токен не коммитить!!!!! ТОКЕН УТЕЧЬ НЕ ДОЛЖЕН

### 5. Запустить бота

```bash
python bot.py
```

Если увидели сообщение `Бот запущен и слушает сообщения...` — всё работает. Откройте MAX и напишите боту `/start`.


## 👤 Автор

**Елена Гордиенко** 

Проект создан в рамках хакатона по разработке чат-ботов для мессенджера MAX.
