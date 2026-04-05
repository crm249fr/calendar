import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler
from datetime import datetime
import calendar
import random
import asyncio
import sqlite3
import os
import json
import requests

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = "8765454976:AAGolrqZ8bcQJTj8FnCN1ltagpM0TBbNGDk"

YANDEX_API_KEY = "AQVN3pZhoIJM9PX_TV-U11qoIbKYsuNlhCCk0048"  
YANDEX_FOLDER_ID = "b1gn6ped0id50712c11g”  

CHOOSING_GIFT, WAITING_PREFERENCES, GETTING_NEW_PREFERENCES = range(3)

# Константы
MONTHS_RU = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
             'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']

def init_database():
    # базы данных smartnotes
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
    #Сохраняет выбранную дату в таблицу пользователя
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
    #Обновляет запись с подарком
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
    #Обновляет предпочтения для записи
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
    #Получает последние даты пользователя
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
    #Получает общее количество дат пользователя
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
    #Получает ID последней записи пользователя
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
    #Получает предпочтения из последней записи
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

def create_calendar(year: int, month: int):
    #Создает клавиатуру календаря
    keyboard = []
    
    keyboard.append([InlineKeyboardButton(f"📅 {MONTHS_RU[month-1]} {year}", callback_data="ignore")])
    
    week_days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    week_row = []
    for day in week_days:
        week_row.append(InlineKeyboardButton(day, callback_data="ignore"))
    keyboard.append(week_row)
    
    cal = calendar.monthcalendar(year, month)
    for week in cal:
        week_row = []
        for day in week:
            if day == 0:
                week_row.append(InlineKeyboardButton(" ", callback_data="ignore"))
            else:
                week_row.append(InlineKeyboardButton(str(day), callback_data=f"date_{year}_{month}_{day}"))
        keyboard.append(week_row)
    
    nav_row = []
    
    prev_year = year - 1 if month == 1 else year
    prev_month = 12 if month == 1 else month - 1
    nav_row.append(InlineKeyboardButton("◀️", callback_data=f"nav_{prev_year}_{prev_month}"))
    
    nav_row.append(InlineKeyboardButton("📅 Сегодня", callback_data="today"))
    
    next_year = year + 1 if month == 12 else year
    next_month = 1 if month == 12 else month + 1
    nav_row.append(InlineKeyboardButton("▶️", callback_data=f"nav_{next_year}_{next_month}"))
    
    keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("❌ Закрыть", callback_data="close")])
    
    return InlineKeyboardMarkup(keyboard)

def get_gift_suggestions(preferences):
    #Получает предложения подарков от Yandex AI
    try:
        # Формируем промпт для Yandex AI
        prompt = f"""
        На основе следующих предпочтений предложи 3 варианта подарков:
        
        {preferences}
        
        Пожалуйста, дай ответ в формате:
        1. [Название подарка] - [краткое описание и цена]
        2. [Название подарка] - [краткое описание и цена]
        3. [Название подарка] - [краткое описание и цена]
        
        Будь конкретным и практичным в предложениях.
        """
        
        # Запрос к Yandex AI API
        url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        headers = {
            "Authorization": f"Api-Key {YANDEX_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt-lite",
            "completionOptions": {
                "stream": False,
                "temperature": 0.7,
                "maxTokens": 1000
            },
            "messages": [
                {
                    "role": "system",
                    "text": "Ты - эксперт по подаркам. Твоя задача - предлагать интересные и уместные варианты подарков на основе предпочтений человека."
                },
                {
                    "role": "user",
                    "text": prompt
                }
            ]
        }
        
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            result = response.json()
            suggestions = result['result']['alternatives'][0]['message']['text']
            return suggestions
        else:
            logger.error(f"Ошибка API Yandex: {response.status_code}")
            return "Извините, временно не могу предложить варианты подарков. Пожалуйста, попробуйте позже."
            
    except Exception as e:
        logger.error(f"Ошибка при получении предложений подарков: {e}")
        return "Произошла ошибка при генерации предложений. Пожалуйста, попробуйте позже."

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #Обработчик команды /start
    try:
        user = update.effective_user
        username = user.username or user.first_name
        
        # Получаем или создаем пользователя в БД
        user_id = get_or_create_user(username)
        
        if user_id:
            context.user_data['db_user_id'] = user_id
            logger.info(f"Пользователь {username} (ID в БД: {user_id}) запустил бота")
        
        keyboard = [[InlineKeyboardButton("📅 Выбрать дату", callback_data='show_calendar')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"Привет, {user.first_name}! 👋\n"
            "Я бот для выбора дат и подбора подарков\n"
            "Используй /choose_date для календаря\n"
            "Или /my_dates для просмотра сохраненных дат",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Ошибка в start: {e}")

async def choose_date_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #Обработчик команды /choose_date
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
    #Обработчик команды /my_dates - показывает сохраненные даты пользователя
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
    #Обработчик команды /hello
    try:
        await update.message.reply_text("Привет! 🎉")
    except Exception as e:
        logger.error(f"Ошибка в hello: {e}")

async def gift_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #Обработчик выбора помощи с подарком
    try:
        query = update.callback_query
        await query.answer()
        
        choice = query.data
        
        if choice == "need_gift_help":
            # Пользователь хочет помощи с подарком
            await query.edit_message_text(
                "🎁 Отлично! Расскажите подробнее о человеке:\n\n"
                "Что ему/ей нравится?\n"
                "• Любимые фильмы/сериалы/аниме/мангу\n"
                "• Любимые персонажи\n"
                "• Увлечения и хобби\n"
                "• Какой тип подарка вы хотите подарить (книга, кружка, толстовка, сладости)\n"
                "• Ваш бюджет на подарок\n\n"
                "Напишите все в одном сообщении:"
            )
            return WAITING_PREFERENCES
            
        elif choice == "no_gift_help":
            # Пользователь не хочет помощи с подарком
            await query.edit_message_text(
                "✅ Хорошо! Дата сохранена без подарка.\n"
                "Если передумаете, можете использовать /choose_date для выбора другой даты."
            )
            return ConversationHandler.END
            
    except Exception as e:
        logger.error(f"Ошибка в gift_choice_callback: {e}")
        return ConversationHandler.END

async def receive_preferences(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #Получает предпочтения пользователя и генерирует предложения подарков
    try:
        preferences = update.message.text
        user = update.effective_user
        username = user.username or user.first_name
        
        user_id = get_or_create_user(username)
        
        if user_id:
            # Получаем ID последней записи
            record_id = context.user_data.get('last_record_id')
            
            if record_id:
                # Сохраняем предпочтения
                update_preferences_for_record(record_id, user_id, preferences)
                
                # Отправляем сообщение о генерации
                waiting_message = await update.message.reply_text(
                    "🔄 Генерирую варианты подарков... Это может занять несколько секунд."
                )
                
                # Получаем предложения подарков
                suggestions = get_gift_suggestions(preferences)
                
                # Удаляем сообщение о ожидании
                await waiting_message.delete()
                
                # Создаем кнопки для взаимодействия
                keyboard = [
                    [InlineKeyboardButton("👍 Мне нравится", callback_data=f"like_gift_{record_id}")],
                    [InlineKeyboardButton("🔄 Найти другие", callback_data=f"find_more_{record_id}")],
                    [InlineKeyboardButton("✏️ Сменить предпочтения", callback_data=f"change_prefs_{record_id}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Сохраняем текущие предложения в context.user_data
                context.user_data['current_suggestions'] = suggestions
                context.user_data['current_preferences'] = preferences
                
                await update.message.reply_text(
                    f"🎁 Вот варианты подарков на основе ваших предпочтений:\n\n{suggestions}\n\n"
                    f"Выберите действие:",
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text("❌ Ошибка: не найдена запись для сохранения подарка.")
        else:
            await update.message.reply_text("❌ Ошибка при получении данных пользователя.")
            
    except Exception as e:
        logger.error(f"Ошибка в receive_preferences: {e}")
        await update.message.reply_text("❌ Произошла ошибка. Пожалуйста, попробуйте снова.")
    
    return ConversationHandler.END

async def gift_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #Обработчик действий с подарками
    try:
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith("like_gift_"):
            # Пользователю нравится подарок
            record_id = int(data.split("_")[2])
            user = update.effective_user
            username = user.username or user.first_name
            user_id = get_or_create_user(username)
            
            if user_id:
                suggestions = context.user_data.get('current_suggestions', '')
                update_gift_for_record(record_id, user_id, suggestions)
                
                await query.edit_message_text(
                    f"✅ Отлично! Ваш выбор сохранен!\n\n"
                    f"Выбранный вариант:\n{suggestions}\n\n"
                    f"Подарок привязан к выбранной дате."
                )
            else:
                await query.edit_message_text("❌ Ошибка при сохранении подарка.")
                
        elif data.startswith("find_more_"):
            # Найти другие варианты подарков
            record_id = int(data.split("_")[2])
            preferences = context.user_data.get('current_preferences', '')
            
            if preferences:
                waiting_message = await query.edit_message_text(
                    "🔄 Генерирую новые варианты подарков..."
                )
                
                # Получаем новые предложения
                new_suggestions = get_gift_suggestions(preferences)
                
                # Обновляем текущие предложения
                context.user_data['current_suggestions'] = new_suggestions
                
                keyboard = [
                    [InlineKeyboardButton("👍 Мне нравится", callback_data=f"like_gift_{record_id}")],
                    [InlineKeyboardButton("🔄 Найти другие", callback_data=f"find_more_{record_id}")],
                    [InlineKeyboardButton("✏️ Сменить предпочтения", callback_data=f"change_prefs_{record_id}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"🎁 Вот другие варианты подарков:\n\n{new_suggestions}\n\n"
                    f"Выберите действие:",
                    reply_markup=reply_markup
                )
            else:
                await query.edit_message_text("❌ Не найдены предпочтения. Пожалуйста, начните заново.")
                
        elif data.startswith("change_prefs_"):
            # Сменить предпочтения
            record_id = int(data.split("_")[2])
            context.user_data['changing_prefs_record'] = record_id
            
            await query.edit_message_text(
                "✏️ Пожалуйста, напишите новые предпочтения:\n\n"
                "Что нравится этому человеку?\n"
                "• Любимые фильмы/сериалы/аниме/мангу\n"
                "• Любимые персонажи\n"
                "• Увлечения и хобби\n"
                "• Тип подарка\n"
                "• Бюджет"
            )
            return WAITING_PREFERENCES
            
    except Exception as e:
        logger.error(f"Ошибка в gift_action_callback: {e}")
        await query.edit_message_text("❌ Произошла ошибка. Пожалуйста, попробуйте снова.")
    
    return ConversationHandler.END

async def receive_new_preferences(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #Получает новые предпочтения и генерирует подарки
    try:
        new_preferences = update.message.text
        user = update.effective_user
        username = user.username or user.first_name
        user_id = get_or_create_user(username)
        
        record_id = context.user_data.get('changing_prefs_record')
        
        if user_id and record_id:
            # Обновляем предпочтения
            update_preferences_for_record(record_id, user_id, new_preferences)
            
            waiting_message = await update.message.reply_text(
                "🔄 Генерирую варианты подарков на основе новых предпочтений..."
            )
            
            # Получаем предложения
            suggestions = get_gift_suggestions(new_preferences)
            
            await waiting_message.delete()
            
            # Обновляем контекст
            context.user_data['current_suggestions'] = suggestions
            context.user_data['current_preferences'] = new_preferences
            
            keyboard = [
                [InlineKeyboardButton("👍 Мне нравится", callback_data=f"like_gift_{record_id}")],
                [InlineKeyboardButton("🔄 Найти другие", callback_data=f"find_more_{record_id}")],
                [InlineKeyboardButton("✏️ Сменить предпочтения", callback_data=f"change_prefs_{record_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"🎁 Вот новые варианты подарков:\n\n{suggestions}\n\n"
                f"Выберите действие:",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text("❌ Ошибка: не найдена запись для обновления.")
            
    except Exception as e:
        logger.error(f"Ошибка в receive_new_preferences: {e}")
        await update.message.reply_text("❌ Произошла ошибка. Пожалуйста, попробуйте снова.")
    
    return ConversationHandler.END

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #Обработчик нажатий на кнопки
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
            _, year, month, day = data.split("_")
            selected_date = f"{day}.{month}.{year}"
            
            user = update.effective_user
            username = user.username or user.first_name
            
            user_id = get_or_create_user(username)
            
            if user_id:
                # Сохраняем дату
                record_id = save_user_date(user_id, int(year), int(month), int(day))
                
                if record_id:
                    total_count = get_user_dates_count(user_id)
                    context.user_data['last_record_id'] = record_id
                    
                    # Спрашиваем о помощи с подарком
                    keyboard = [
                        [InlineKeyboardButton("🎁 Да, помоги подобрать подарок", callback_data="need_gift_help")],
                        [InlineKeyboardButton("❌ Нет, просто сохранить дату", callback_data="no_gift_help")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(
                        text=f"✅ Дата {selected_date} сохранена!\n"
                             f"Всего дат: {total_count}\n\n"
                             f"Хотите, чтобы я помог подобрать подарок?",
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
            await query.edit_message_text(text="❌ Календарь закрыт")
    
    except Exception as e:
        logger.error(f"Ошибка в button_callback: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #Обработчик обычных текстовых сообщений
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
    
    # Проверка наличия API ключей
    if YANDEX_API_KEY == "ваш_ключ_api" or YANDEX_FOLDER_ID == "ваш_folder_id":
        print("⚠️ ВНИМАНИЕ: Не настроены API ключи для Yandex AI!")
        print("Пожалуйста, укажите YANDEX_API_KEY и YANDEX_FOLDER_ID в коде")
    
    init_database()
    print("✅ База данных инициализирована")
    
    app = Application.builder().token(TOKEN).build()
    
    # Добавляем команды
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("hello", hello_command))
    app.add_handler(CommandHandler("choose_date", choose_date_command))
    app.add_handler(CommandHandler("my_dates", my_dates_command))
    
    # Conversation handler для подбора подарков
    gift_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(gift_choice_callback, pattern="^(need_gift_help|no_gift_help)$")],
        states={
            WAITING_PREFERENCES: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_preferences)],
        },
        fallbacks=[CommandHandler("cancel", lambda u,c: u.message.reply_text("Действие отменено"))],
    )
    
    # Добавляем обработчики
    app.add_handler(CallbackQueryHandler(button_callback, pattern="^(?!need_gift_help|no_gift_help|like_gift_|find_more_|change_prefs_).*"))
    app.add_handler(CallbackQueryHandler(gift_action_callback, pattern="^(like_gift_|find_more_|change_prefs_)"))
    app.add_handler(gift_conv_handler)
    
    # Обработчик для смены предпочтений
    change_prefs_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(gift_action_callback, pattern="^change_prefs_")],
        states={
            WAITING_PREFERENCES: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_preferences)],
        },
        fallbacks=[CommandHandler("cancel", lambda u,c: u.message.reply_text("Изменение предпочтений отменено"))],
    )
    app.add_handler(change_prefs_handler)
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.add_error_handler(error_handler)
    
    print("✅ Бот запущен! Доступные команды: /start, /hello, /choose_date, /my_dates")
    print("📊 Данные сохраняются в файл smartnotes.db")
    print("🎁 Добавлена функция подбора подарков с помощью Yandex AI")
    print("⚠️ Нажмите Ctrl+C для остановки.")
    
    app.run_polling(
        allowed_updates=['message', 'callback_query'],
        drop_pending_updates=True,
        timeout=30
    )

if __name__ == "__main__":
    main()
