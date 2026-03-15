import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from datetime import datetime
import calendar
import random
import asyncio
import sqlite3
import os

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = "8765454976:AAGolrqZ8bcQJTj8FnCN1ltagpM0TBbNGDk"

# Константы
MONTHS_RU = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
             'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']

def init_database():
    """
    Инициализация базы данных smartnotes
    Создает таблицу users, если она не существует
    """
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
    """
    Получает ID пользователя из таблицы users или создает нового
    Возвращает ID пользователя
    """
    conn = None
    try:
        conn = sqlite3.connect('smartnotes.db')
        cursor = conn.cursor()
        
        # Ищем пользователя по username
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        
        if result:
            # Пользователь найден, возвращаем его ID
            user_id = result[0]
            logger.info(f"Найден существующий пользователь: {username} с ID {user_id}")
        else:
            # Создаем нового пользователя
            cursor.execute("INSERT INTO users (username) VALUES (?)", (username,))
            user_id = cursor.lastrowid
            conn.commit()
            logger.info(f"Создан новый пользователь: {username} с ID {user_id}")
            
            # Создаем таблицу для пользователя с именем = его ID
            create_user_table(user_id)
        
        return user_id
        
    except Exception as e:
        logger.error(f"Ошибка при получении/создании пользователя: {e}")
        return None
    finally:
        if conn:
            conn.close()

def create_user_table(user_id):
    """
    Создает таблицу для пользователя с именем = user_id
    Таблица имеет структуру как в таблице "1"
    """
    conn = None
    try:
        conn = sqlite3.connect('smartnotes.db')
        cursor = conn.cursor()
        
        # Создаем таблицу с именем = ID пользователя
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS "{user_id}" (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                day INTEGER NOT NULL,
                time TEXT,
                event TEXT,
                whom TEXT,
                what_gift TEXT
            )
        ''')
        
        conn.commit()
        logger.info(f"Создана таблица для пользователя с ID {user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка при создании таблицы пользователя: {e}")
    finally:
        if conn:
            conn.close()

def save_user_date(user_id, year, month, day):
    """
    Сохраняет выбранную дату в таблицу пользователя
    """
    conn = None
    try:
        conn = sqlite3.connect('smartnotes.db')
        cursor = conn.cursor()
        
        # Вставляем дату в таблицу пользователя
        cursor.execute(f'''
            INSERT INTO "{user_id}" (year, month, day)
            VALUES (?, ?, ?)
        ''', (year, month, day))
        
        conn.commit()
        logger.info(f"Дата {day}.{month}.{year} сохранена для пользователя {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении даты: {e}")
        return False
    finally:
        if conn:
            conn.close()

def get_user_dates(user_id, limit=5):
    """
    Получает последние даты пользователя
    """
    conn = None
    try:
        conn = sqlite3.connect('smartnotes.db')
        cursor = conn.cursor()
        
        # Проверяем, существует ли таблица пользователя
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (str(user_id),))
        if not cursor.fetchone():
            return []
        
        # Получаем последние даты
        cursor.execute(f'''
            SELECT year, month, day FROM "{user_id}"
            ORDER BY id DESC
            LIMIT ?
        ''', (limit,))
        
        dates = cursor.fetchall()
        
        # Форматируем даты для вывода
        formatted_dates = [f"{day}.{month}.{year}" for year, month, day in dates]
        return formatted_dates
        
    except Exception as e:
        logger.error(f"Ошибка при получении дат пользователя: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_user_dates_count(user_id):
    """
    Получает общее количество дат пользователя
    """
    conn = None
    try:
        conn = sqlite3.connect('smartnotes.db')
        cursor = conn.cursor()
        
        # Проверяем, существует ли таблица пользователя
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
def create_calendar(year: int, month: int):
    """Создает клавиатуру календаря"""
    keyboard = []
    
    # Заголовок с месяцем и годом
    keyboard.append([InlineKeyboardButton(f"📅 {MONTHS_RU[month-1]} {year}", callback_data="ignore")])
    
    # Дни недели
    week_days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    week_row = []
    for day in week_days:
        week_row.append(InlineKeyboardButton(day, callback_data="ignore"))
    keyboard.append(week_row)
    
    # Дни месяца
    cal = calendar.monthcalendar(year, month)
    for week in cal:
        week_row = []
        for day in week:
            if day == 0:
                week_row.append(InlineKeyboardButton(" ", callback_data="ignore"))
            else:
                week_row.append(InlineKeyboardButton(str(day), callback_data=f"date_{year}_{month}_{day}"))
        keyboard.append(week_row)
    
    # Навигация
    nav_row = []
    
    prev_year = year - 1 if month == 1 else year
    prev_month = 12 if month == 1 else month - 1
    nav_row.append(InlineKeyboardButton("◀️", callback_data=f"nav_{prev_year}_{prev_month}"))
    
    nav_row.append(InlineKeyboardButton("📅 Сегодня", callback_data="today"))
    
    next_year = year + 1 if month == 12 else year
    next_month = 1 if month == 12 else month + 1
    nav_row.append(InlineKeyboardButton("▶️", callback_data=f"nav_{next_year}_{next_month}"))
    
    keyboard.append(nav_row)
    
    # Кнопка закрытия
    keyboard.append([InlineKeyboardButton("❌ Закрыть", callback_data="close")])
    
    return InlineKeyboardMarkup(keyboard)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    try:
        user = update.effective_user
        username = user.username or user.first_name  # Используем first_name, если нет username
        
        # Получаем или создаем пользователя в БД
        user_id = get_or_create_user(username)
        
        if user_id:
            # Сохраняем user_id в context.user_data для дальнейшего использования
            context.user_data['db_user_id'] = user_id
            logger.info(f"Пользователь {username} (ID в БД: {user_id}) запустил бота")
        
        keyboard = [[InlineKeyboardButton("📅 Выбрать дату", callback_data='show_calendar')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"Привет, {user.first_name}! 👋\n"
            "Я бот для выбора дат\n"
            "Используй /choose_date для календаря",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Ошибка в start: {e}")

async def choose_date_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /choose_date"""
    try:
        now = datetime.now()
        calendar_markup = create_calendar(now.year, now.month)
        
        await update.message.reply_text(
            "📆 Выберите дату:",
            reply_markup=calendar_markup
        )
    except Exception as e:
        logger.error(f"Ошибка в choose_date: {e}")

async def my_dates_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /my_dates - показывает сохраненные даты пользователя"""
    try:
        user = update.effective_user
        username = user.username or user.first_name
        
        # Получаем ID пользователя из БД
        user_id = get_or_create_user(username)
        
        if user_id:
            # Получаем даты пользователя из БД
            dates = get_user_dates(user_id)
            total_count = get_user_dates_count(user_id)
            
            if dates:
                dates_list = "\n".join([f"• {date}" for date in dates])
                await update.message.reply_text(
                    f"📅 Ваши последние даты:\n\n{dates_list}\n\n"
                    f"Всего дат: {total_count}"
                )
            else:
                await update.message.reply_text("У вас пока нет сохраненных дат.")
        else:
            await update.message.reply_text("Ошибка при получении данных пользователя.")
            
    except Exception as e:
        logger.error(f"Ошибка в my_dates: {e}")

async def hello_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /hello"""
    try:
        await update.message.reply_text("Привет! 🎉")
    except Exception as e:
        logger.error(f"Ошибка в hello: {e}")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    try:
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "ignore":
            return
        
        elif data == "show_calendar":
            # Показать календарь
            now = datetime.now()
            calendar_markup = create_calendar(now.year, now.month)
            await query.edit_message_text(
                text="📆 Выберите дату:",
                reply_markup=calendar_markup
            )
        
        elif data == "today":
            # Перейти к текущему месяцу
            now = datetime.now()
            calendar_markup = create_calendar(now.year, now.month)
            await query.edit_message_text(
                text="📆 Выберите дату:",
                reply_markup=calendar_markup
            )
        
        elif data.startswith("nav_"):
            # Навигация по месяцам
            _, year, month = data.split("_")
            calendar_markup = create_calendar(int(year), int(month))
            await query.edit_message_text(
                text="📆 Выберите дату:",
                reply_markup=calendar_markup
            )
        
        elif data.startswith("date_"):
            # Выбрана конкретная дата
            _, year, month, day = data.split("_")
            selected_date = f"{day}.{month}.{year}"
            
            # Получаем информацию о пользователе
            user = update.effective_user
            username = user.username or user.first_name
            
            # Получаем или создаем пользователя в БД
            user_id = get_or_create_user(username)
            
            if user_id:
                # Сохраняем дату в БД
                save_success = save_user_date(user_id, int(year), int(month), int(day))
                
                if save_success:
                    # Получаем общее количество дат
                    total_count = get_user_dates_count(user_id)
                    
                    await query.edit_message_text(
                        text=f"✅ Дата {selected_date} сохранена в базе данных!\n"
                             f"Всего дат: {total_count}"
                    )
                    
                    # Предлагаем выбрать еще дату
                    keyboard = [[InlineKeyboardButton("📅 Выбрать еще", callback_data='show_calendar')]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await context.bot.send_message(
                        chat_id=update.effective_user.id,
                        text="Хотите выбрать еще дату?",
                        reply_markup=reply_markup
                    )
                else:
                    await query.edit_message_text(
                        text="❌ Ошибка при сохранении даты в базе данных."
                    )
            else:
                await query.edit_message_text(
                    text="❌ Ошибка при получении данных пользователя."
                )
        
        elif data == "close":
            # Закрыть календарь
            await query.edit_message_text(text="❌ Календарь закрыт")
    
    except Exception as e:
        logger.error(f"Ошибка в button_callback: {e}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик обычных текстовых сообщений"""
    try:
        responses = ["Привет! 😊", "Здравствуй! 🌟", "Привет-привет! 🎈"]
        response = random.choice(responses)
        
        keyboard = [[InlineKeyboardButton("📅 Выбрать дату", callback_data='show_calendar')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(response, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Ошибка в handle_message: {e}")
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Глобальный обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}")
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Произошла ошибка. Попробуйте еще раз."
            )
    except:
        pass

def main():
    print("Запускаю бота...")
    
    # Инициализируем базу данных
    init_database()
    print("✅ База данных инициализирована")
    
    # Создаем приложение
    app = Application.builder().token(TOKEN).build()
    
    # Регистрируем обработчики команд
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("hello", hello_command))
    app.add_handler(CommandHandler("choose_date", choose_date_command))
    app.add_handler(CommandHandler("my_dates", my_dates_command))
    
    # Регистрируем обработчик callback-запросов (кнопки)
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Регистрируем обработчик текстовых сообщений
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Регистрируем глобальный обработчик ошибок
    app.add_error_handler(error_handler)
    
    print("✅ Бот запущен! Доступные команды: /start, /hello, /choose_date, /my_dates")
    print("📊 Данные сохраняются в файл smartnotes.db")
    print("⚠️ Нажмите Ctrl+C для остановки.")
    
    # Запускаем бота
    app.run_polling(
        allowed_updates=['message', 'callback_query'],
        drop_pending_updates=True,
        timeout=30
    )

if __name__ == "__main__":
    main()