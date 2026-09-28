import aiosqlite

DB_PATH = "bot_database.db"

async def init_db():
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                interests TEXT
            )
        """)
        await db.commit()
    print("База данных готова.")

async def save_interests(user_id: int, interests: list[str]):

    
    interests_str = ",".join(interests)
    
    async with aiosqlite.connect(DB_PATH) as db:
        
        await db.execute("""
            INSERT OR REPLACE INTO users (user_id, interests)
            VALUES (?, ?)
        """, (user_id, interests_str))
        await db.commit()

async def get_interests(user_id: int) -> list[str]:
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT interests FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row and row["interests"]:
                result = row["interests"].split(",")
                return result
            return []