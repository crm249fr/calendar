import logging
import requests
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler
from datetime import datetime
import calendar
import random
import asyncio

from API import TOKEN, YANDEX_API_KEY, YANDEX_FOLDER_ID, MONTHS_RU, CHOOSING_GIFT, WAITING_PREFERENCES, GETTING_NEW_PREFERENCES, API_HOST, API_PORT

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

API_BASE_URL = f"http://{API_HOST}:{API_PORT}/api"

class DatabaseAPI:
    """Клиент для работы с Flask-RESTful API"""
    
    @staticmethod
    def get_or_create_user(username):
        """Получение или создание пользователя через API"""
        try:
            response = requests.post(
                f"{API_BASE_URL}/users",
                json={'username': username},
                timeout=10
            )
            if response.status_code == 200:
                return response.json().get('user_id')
            else:
                logger.error(f"API error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error in get_or_create_user: {e}")
            return None
    
    @staticmethod
    def save_user_date(user_id, year, month, day, event=None, whom=None, what_gift=None):
        """Сохранение даты через API"""
        try:
            response = requests.post(
                f"{API_BASE_URL}/users/{user_id}/dates",
                json={
                    'year': year,
                    'month': month,
                    'day': day,
                    'event': event,
                    'whom': whom,
                    'what_gift': what_gift
                },
                timeout=10
            )
            if response.status_code == 201:
                return response.json().get('record_id')
            else:
                logger.error(f"API error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error in save_user_date: {e}")
            return None
    
    @staticmethod
    def get_user_dates(user_id, limit=5):
        """Получение дат пользователя через API"""
        try:
            response = requests.get(
                f"{API_BASE_URL}/users/{user_id}/dates",
                params={'limit': limit},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return data.get('dates', []), data.get('count', 0)
            else:
                logger.error(f"API error: {response.status_code} - {response.text}")
                return [], 0
        except Exception as e:
            logger.error(f"Error in get_user_dates: {e}")
            return [], 0
    
    @staticmethod
    def update_gift(record_id, user_id, what_gift):
        """Обновление подарка через API"""
        try:
            response = requests.put(
                f"{API_BASE_URL}/users/{user_id}/dates/{record_id}/gift",
                json={'what_gift': what_gift},
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error in update_gift: {e}")
            return False
    
    @staticmethod
    def update_preferences(record_id, user_id, preferences):
        """Обновление предпочтений через API"""
        try:
            response = requests.put(
                f"{API_BASE_URL}/users/{user_id}/dates/{record_id}/preferences",
                json={'preferences': preferences},
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error in update_preferences: {e}")
            return False
    
    @staticmethod
    def get_last_preferences(user_id):
        """Получение последних предпочтений через API"""
        try:
            response = requests.get(
                f"{API_BASE_URL}/users/{user_id}/preferences",
                timeout=10
            )
            if response.status_code == 200:
                return response.json().get('preferences')
            return None
        except Exception as e:
            logger.error(f"Error in get_last_preferences: {e}")
            return None
    
    @staticmethod
    def get_record(user_id, record_id):
        """Получение записи через API"""
        try:
            response = requests.get(
                f"{API_BASE_URL}/users/{user_id}/records/{record_id}",
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Error in get_record: {e}")
            return None
    
    @staticmethod
    def get_user_stats(user_id):
        """Получение статистики пользователя через API"""
        try:
            response = requests.get(
                f"{API_BASE_URL}/users/{user_id}/stats",
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Error in get_user_stats: {e}")
            return None

db_api = DatabaseAPI()

def create_calendar(year: int, month: int):
    """Создает клавиатуру календаря"""
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
    """Получает предложения подарков от Yandex AI"""
    try:
        prompt = f"""
        На основе следующих предпочтений предложи 3 варианта подарков:
        
        {preferences}
        
        Пожалуйста, дай ответ в формате:
        1. [Название подарка] - [краткое описание и цена]
        2. [Название подарка] - [краткое описание и цена]
        3. [Название подарка] - [краткое описание и цена]
        
        Будь конкретным и практичным в предложениях.
        """
        
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
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
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
    """Обработчик команды /start"""
    try:
        user = update.effective_user
        username = user.username or user.first_name
        
        user_id = db_api.get_or_create_user(username)
        
        if user_id:
            context.user_data['db_user_id'] = user_id
            logger.info(f"Пользователь {username} (ID в БД: {user_id}) запустил бота")
            
            # Получаем статистику
            stats = db_api.get_user_stats(user_id)
            stats_text = ""
            if stats:
                stats_text = f"\n📊 Статистика: {stats.get('total_dates', 0)} дат, {stats.get('dates_with_gifts', 0)} с подарками"
        
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
    """Обработчик команды /my_dates"""
    try:
        user = update.effective_user
        username = user.username or user.first_name
        
        user_id = db_api.get_or_create_user(username)
        
        if user_id:
            dates, total_count = db_api.get_user_dates(user_id)
            
            if dates:
                dates_list = []
                for date in dates[:5]:
                    date_str = f"{date['day']}.{date['month']}.{date['year']}"
                    if date.get('what_gift'):
                        date_str += f" (Подарок: {date['what_gift'][:50]}...)"
                    dates_list.append(f"• {date_str}")
                
                dates_text = "\n".join(dates_list)
                await update.message.reply_text(
                    f"📅 Ваши последние даты:\n\n{dates_text}\n\n"
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

async def gift_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора помощи с подарком"""
    try:
        query = update.callback_query
        await query.answer()
        
        choice = query.data
        
        if choice == "need_gift_help":
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
            await query.edit_message_text(
                "✅ Хорошо! Дата сохранена без подарка.\n"
                "Если передумаете, можете использовать /choose_date для выбора другой даты."
            )
            return ConversationHandler.END
            
    except Exception as e:
        logger.error(f"Ошибка в gift_choice_callback: {e}")
        return ConversationHandler.END

async def receive_preferences(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получает предпочтения пользователя и генерирует предложения подарков"""
    try:
        preferences = update.message.text
        user = update.effective_user
        username = user.username or user.first_name
        
        user_id = db_api.get_or_create_user(username)
        
        if user_id:
            record_id = context.user_data.get('last_record_id')
            
            if record_id:
                db_api.update_preferences(record_id, user_id, preferences)
                
                waiting_message = await update.message.reply_text(
                    "🔄 Генерирую варианты подарков... Это может занять несколько секунд."
                )
                
                suggestions = get_gift_suggestions(preferences)
                
                await waiting_message.delete()
                
                keyboard = [
                    [InlineKeyboardButton("👍 Мне нравится", callback_data=f"like_gift_{record_id}")],
                    [InlineKeyboardButton("🔄 Найти другие", callback_data=f"find_more_{record_id}")],
                    [InlineKeyboardButton("✏️ Сменить предпочтения", callback_data=f"change_prefs_{record_id}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
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
    """Обработчик действий с подарками"""
    try:
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith("like_gift_"):
            record_id = int(data.split("_")[2])
            user = update.effective_user
            username = user.username or user.first_name
            user_id = db_api.get_or_create_user(username)
            
            if user_id:
                suggestions = context.user_data.get('current_suggestions', '')
                success = db_api.update_gift(record_id, user_id, suggestions)
                
                if success:
                    await query.edit_message_text(
                        f"✅ Отлично! Ваш выбор сохранен!\n\n"
                        f"Выбранный вариант:\n{suggestions}\n\n"
                        f"Подарок привязан к выбранной дате."
                    )
                else:
                    await query.edit_message_text("❌ Ошибка при сохранении подарка.")
            else:
                await query.edit_message_text("❌ Ошибка при сохранении подарка.")
                
        elif data.startswith("find_more_"):
            record_id = int(data.split("_")[2])
            preferences = context.user_data.get('current_preferences', '')
            
            if preferences:
                waiting_message = await query.edit_message_text(
                    "🔄 Генерирую новые варианты подарков..."
                )
                
                new_suggestions = get_gift_suggestions(preferences)
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
    """Получает новые предпочтения и генерирует подарки"""
    try:
        new_preferences = update.message.text
        user = update.effective_user
        username = user.username or user.first_name
        user_id = db_api.get_or_create_user(username)
        
        record_id = context.user_data.get('changing_prefs_record')
        
        if user_id and record_id:
            db_api.update_preferences(record_id, user_id, new_preferences)
            
            waiting_message = await update.message.reply_text(
                "🔄 Генерирую варианты подарков на основе новых предпочтений..."
            )
            
            suggestions = get_gift_suggestions(new_preferences)
            
            await waiting_message.delete()
            
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
    """Обработчик нажатий на кнопки"""
    try:
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "ignore":
            return
        
        elif data == "show_calendar":
            now = datetime.now()
            calendar_markup = create_calendar(now.year, now.month)
            await query.edit_message_text(
                text="📆 Выберите дату:",
                reply_markup=calendar_markup
            )
        
        elif data == "today":
            now = datetime.now()
            calendar_markup = create_calendar(now.year, now.month)
            await query.edit_message_text(
                text="📆 Выберите дату:",
                reply_markup=calendar_markup
            )
        
        elif data.startswith("nav_"):
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
            
            user_id = db_api.get_or_create_user(username)
            
            if user_id:
                record_id = db_api.save_user_date(user_id, int(year), int(month), int(day))
                
                if record_id:
                    _, total_count = db_api.get_user_dates(user_id, 1)
                    context.user_data['last_record_id'] = record_id
                    
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
    print("🤖 Запускаю Telegram бота...")
    
    # Проверка API ключей
    if YANDEX_API_KEY == "ваш_ключ_api" or YANDEX_FOLDER_ID == "ваш_folder_id":
        print("⚠️ ВНИМАНИЕ: Не настроены API ключи для Yandex AI!")
    
    # Проверка доступности API сервера
    try:
        response = requests.get(f"{API_BASE_URL}/users", timeout=5)
        print("✅ API сервер доступен")
    except:
        print("⚠️ ВНИМАНИЕ: API сервер недоступен!")
        print(f"Убедитесь, что database_api.py запущен на {API_HOST}:{API_PORT}")
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("hello", hello_command))
    app.add_handler(CommandHandler("choose_date", choose_date_command))
    app.add_handler(CommandHandler("my_dates", my_dates_command))
    
    gift_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(gift_choice_callback, pattern="^(need_gift_help|no_gift_help)$")],
        states={
            WAITING_PREFERENCES: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_preferences)],
        },
        fallbacks=[CommandHandler("cancel", lambda u,c: u.message.reply_text("Действие отменено"))],
    )
    
    app.add_handler(CallbackQueryHandler(button_callback, pattern="^(?!need_gift_help|no_gift_help|like_gift_|find_more_|change_prefs_).*"))
    app.add_handler(CallbackQueryHandler(gift_action_callback, pattern="^(like_gift_|find_more_|change_prefs_)"))
    app.add_handler(gift_conv_handler)
    
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
    print("🎁 Добавлена функция подбора подарков с помощью Yandex AI")
    print("⚠️ Нажмите Ctrl+C для остановки.")
    
    app.run_polling(
        allowed_updates=['message', 'callback_query'],
        drop_pending_updates=True,
        timeout=30
    )

if __name__ == "__main__":
    main()