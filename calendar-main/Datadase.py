import sqlite3
import logging

logger = logging.getLogger(__name__)

def init_database():
    try:
        conn = sqlite3.connect('smartnotes.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL
            )
        ''')
        
        conn.commit()
        logger.info("База данных успешно инициализирована")
        return conn
        
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        return None

def get_or_create_user(username):
    conn = None
    try:
        conn = sqlite3.connect('smartnotes.db')
        cursor = conn.cursor()
      
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        
        if result:
            user_id = result[0]
            logger.info(f"Найден существующий пользователь: {username} с ID {user_id}")
        else:
            cursor.execute("INSERT INTO users (username) VALUES (?)", (username,))
            user_id = cursor.lastrowid
            conn.commit()
            logger.info(f"Создан новый пользователь: {username} с ID {user_id}")
            
            create_user_table(user_id)
        
        return user_id
        
    except Exception as e:
        logger.error(f"Ошибка при получении/создании пользователя: {e}")
        return None
    finally:
        if conn:
            conn.close()

def create_user_table(user_id):
    conn = None
    try:
        conn = sqlite3.connect('smartnotes.db')
        cursor = conn.cursor()
        
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS "{user_id}" (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                day INTEGER NOT NULL,
                time TEXT,
                event TEXT,
                whom TEXT,
                what_gift TEXT,
                preferences TEXT
            )
        ''')
        
        conn.commit()
        logger.info(f"Создана таблица для пользователя с ID {user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка при создании таблицы пользователя: {e}")
    finally:
        if conn:
            conn.close()

def save_user_date(user_id, year, month, day, event=None, whom=None, what_gift=None):
    conn = None
    try:
        conn = sqlite3.connect('smartnotes.db')
        cursor = conn.cursor()
        
        cursor.execute(f'''
            INSERT INTO "{user_id}" (year, month, day, event, whom, what_gift)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (year, month, day, event, whom, what_gift))
        
        conn.commit()
        logger.info(f"Дата {day}.{month}.{year} сохранена для пользователя {user_id}")
        
        cursor.execute(f"SELECT last_insert_rowid()")
        record_id = cursor.fetchone()[0]
        
        return record_id
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении даты: {e}")
        return None
    finally:
        if conn:
            conn.close()

def update_gift_for_record(record_id, user_id, what_gift):
    conn = None
    try:
        conn = sqlite3.connect('smartnotes.db')
        cursor = conn.cursor()
        
        cursor.execute(f'''
            UPDATE "{user_id}"
            SET what_gift = ?
            WHERE id = ?
        ''', (what_gift, record_id))
        
        conn.commit()
        logger.info(f"Подарок сохранен для записи {record_id} пользователя {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при обновлении подарка: {e}")
        return False
    finally:
        if conn:
            conn.close()

def update_preferences_for_record(record_id, user_id, preferences):
    conn = None
    try:
        conn = sqlite3.connect('smartnotes.db')
        cursor = conn.cursor()
        
        cursor.execute(f'''
            UPDATE "{user_id}"
            SET preferences = ?
            WHERE id = ?
        ''', (preferences, record_id))
        
        conn.commit()
        logger.info(f"Предпочтения сохранены для записи {record_id}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при обновлении предпочтений: {e}")
        return False
    finally:
        if conn:
            conn.close()

def get_user_dates(user_id, limit=5):
    conn = None
    try:
        conn = sqlite3.connect('smartnotes.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (str(user_id),))
        if not cursor.fetchone():
            return []
        
        cursor.execute(f'''
            SELECT year, month, day, what_gift FROM "{user_id}"
            ORDER BY id DESC
            LIMIT ?
        ''', (limit,))
        
        dates = cursor.fetchall()
        
        formatted_dates = []
        for year, month, day, what_gift in dates:
            date_str = f"{day}.{month}.{year}"
            if what_gift:
                date_str += f" (Подарок: {what_gift[:50]}...)"
            formatted_dates.append(date_str)
        
        return formatted_dates
        
    except Exception as e:
        logger.error(f"Ошибка при получении дат пользователя: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_user_dates_count(user_id):
    conn = None
    try:
        conn = sqlite3.connect('smartnotes.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (str(user_id),))
        if not cursor.fetchone():
            return 0
        
        cursor.execute(f'SELECT COUNT(*) FROM "{user_id}"')
        count = cursor.fetchone()[0]
        return count
        
    except Exception as e:
        logger.error(f"Ошибка при подсчете дат пользователя: {e}")
        return 0
    finally:
        if conn:
            conn.close()

def get_last_record_id(user_id):
    conn = None
    try:
        conn = sqlite3.connect('smartnotes.db')
        cursor = conn.cursor()
        
        cursor.execute(f'''
            SELECT id FROM "{user_id}"
            ORDER BY id DESC
            LIMIT 1
        ''')
        
        result = cursor.fetchone()
        return result[0] if result else None
        
    except Exception as e:
        logger.error(f"Ошибка при получении последней записи: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_last_preferences(user_id):
    conn = None
    try:
        conn = sqlite3.connect('smartnotes.db')
        cursor = conn.cursor()
        
        cursor.execute(f'''
            SELECT preferences FROM "{user_id}"
            ORDER BY id DESC
            LIMIT 1
        ''')
        
        result = cursor.fetchone()
        return result[0] if result and result[0] else None
        
    except Exception as e:
        logger.error(f"Ошибка при получении предпочтений: {e}")
        return None
    finally:
        if conn:
            conn.close()
