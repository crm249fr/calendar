import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler
from datetime import datetime
import calendar
import random
import asyncio
import json
import requests
import re
 
from API import TOKEN, YANDEX_API_KEY, YANDEX_FOLDER_ID, MONTHS_RU, API_BASE_URL
from Database import (
    init_database, get_or_create_user, save_user_date, update_gift_for_record,
    update_preferences_for_record, get_user_dates, get_user_dates_count,
    get_last_record_id, get_last_preferences
)
 
CHOOSING_REMINDER = 4
CHOOSING_GIFT_NUMBER = 5
 
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Функция для вызовов Flask API
def call_api(endpoint, data, timeout=10):
    """Вспомогательная функция для вызовов Flask API"""
    try:
        response = requests.post(f'{API_BASE_URL}/{endpoint}', json=data, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        logger.error(f"Не удается подключиться к Flask API на {API_BASE_URL}")
        return None
    except Exception as e:
        logger.error(f"API error {endpoint}: {e}")
        return None

# Проверка доступности API
def check_api_available():
    try:
        response = requests.get(f'{API_BASE_URL}/health', timeout=5)
        return response.status_code == 200
    except:
        return False
 
def create_calendar(year, month):
    keyboard = []
    keyboard.append([InlineKeyboardButton(f"📅 {MONTHS_RU[month-1]} {year}", callback_data="ignore")])
    week_days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    keyboard.append([InlineKeyboardButton(d, callback_data="ignore") for d in week_days])
    for week in calendar.monthcalendar(year, month):
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data="ignore"))
            else:
                row.append(InlineKeyboardButton(str(day), callback_data=f"date_{year}_{month}_{day}"))
        keyboard.append(row)
    prev_year = year - 1 if month == 1 else year
    prev_month = 12 if month == 1 else month - 1
    next_year = year + 1 if month == 12 else year
    next_month = 1 if month == 12 else month + 1
    keyboard.append([
        InlineKeyboardButton("◀️", callback_data=f"nav_{prev_year}_{prev_month}"),
        InlineKeyboardButton("📅 Сегодня", callback_data="today"),
        InlineKeyboardButton("▶️", callback_data=f"nav_{next_year}_{next_month}")
    ])
    keyboard.append([InlineKeyboardButton("❌ Закрыть", callback_data="close")])
    return InlineKeyboardMarkup(keyboard)
 
 
def parse_gift_suggestions(text):
    gifts = []
    for line in text.split('\n'):
        match = re.match(r'^(\d+)\.\s*(.+)$', line.strip())
        if match:
            gifts.append({'number': int(match.group(1)), 'text': match.group(2)})
    return gifts
 
 
def get_gift_suggestions(preferences):
    try:
        url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        headers = {"Authorization": f"Api-Key {YANDEX_API_KEY}", "Content-Type": "application/json"}
        data = {
            "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt-lite",
            "completionOptions": {"stream": False, "temperature": 0.7, "maxTokens": 1000},
            "messages": [
                {"role": "system", "text": "Ты - эксперт по подаркам."},
                {"role": "user", "text": f"Предложи 3 подарка:\n{preferences}\n\nФормат:\n1. ...\n2. ...\n3. ..."}
            ]
        }
        response = requests.post(url, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            return response.json()['result']['alternatives'][0]['message']['text']
        return "Временно недоступно. Попробуйте позже."
    except Exception as e:
        logger.error(f"Ошибка Yandex AI: {e}")
        return "Произошла ошибка. Попробуйте позже."
  
async def start_command(update, context):
    user = update.effective_user
    # Проверяем доступность API
    if not check_api_available():
        await update.message.reply_text("⚠️ Сервер временно недоступен. Пожалуйста, попробуйте позже.")
        return
    
    result = call_api('get_or_create_user', {'username': user.username or user.first_name})
    if result and result.get('user_id'):
        context.user_data['db_user_id'] = result['user_id']
    keyboard = [[InlineKeyboardButton("📅 Выбрать дату", callback_data='show_calendar')]]
    await update.message.reply_text(
        f"Привет, {user.first_name}! 👋\n\n"
        "Я бот для выбора дат и подбора подарков\n\n"
        "📌 Команды:\n"
        "/choose_date - выбрать дату в календаре\n"
        "/my_dates - посмотреть сохраненные даты\n"
        "/hello - поздороваться",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
 
async def choose_date_command(update, context):
    now = datetime.now()
    await update.message.reply_text("📆 Выберите дату:", reply_markup=create_calendar(now.year, now.month))
 
async def my_dates_command(update, context):
    user = update.effective_user
    if not check_api_available():
        await update.message.reply_text("⚠️ Сервер временно недоступен. Пожалуйста, попробуйте позже.")
        return
    
    result = call_api('get_or_create_user', {'username': user.username or user.first_name})
    if result and result.get('user_id'):
        dates_result = call_api('get_user_dates', {'user_id': result['user_id'], 'limit': 10})
        if dates_result and dates_result.get('dates'):
            dates = dates_result['dates']
            total = dates_result['count']
            await update.message.reply_text(
                f"📅 Ваши сохраненные даты:\n\n" +
                "\n\n".join([f"• {d}" for d in dates]) +
                f"\n\n📊 Всего дат: {total}"
            )
        else:
            await update.message.reply_text("📭 Нет дат. Используйте /choose_date")
    else:
        await update.message.reply_text("📭 Нет дат. Используйте /choose_date")
 
async def hello_command(update, context):
    await update.message.reply_text("Привет! 🎉 Чем могу помочь?")
 
async def gift_choice_callback(update, context):
    query = update.callback_query
    await query.answer()
    if query.data == "need_gift_help":
        await query.edit_message_text(
            "🎁 Расскажите о человеке:\n\n• Любимые фильмы/аниме/персонажи\n"
            "• Хобби\n• Тип подарка\n• Бюджет\n\nНапишите в одном сообщении:"
        )
        return WAITING_PREFERENCES
    elif query.data == "no_gift_help":
        await query.edit_message_text("✅ Дата сохранена без подарка.")
        return ConversationHandler.END
 
async def receive_preferences(update, context):
    preferences = update.message.text
    result = call_api('get_or_create_user', {'username': update.effective_user.username or update.effective_user.first_name})
    user_id = result.get('user_id') if result else None
    record_id = context.user_data.get('last_record_id')
    if user_id and record_id:
        call_api('update_preferences', {'record_id': record_id, 'user_id': user_id, 'preferences': preferences})
        msg = await update.message.reply_text("🔄 Генерирую варианты подарков...")
        suggestions = get_gift_suggestions(preferences)
        await msg.delete()
        gifts = parse_gift_suggestions(suggestions)
        context.user_data.update({'current_gifts': gifts, 'current_preferences': preferences, 'current_record_id': record_id})
        keyboard = [[InlineKeyboardButton(f"🎁 Выбрать вариант {g['number']}", callback_data=f"select_gift_{g['number']}")] for g in gifts]
        keyboard += [
            [InlineKeyboardButton("🔄 Найти другие", callback_data=f"find_more_{record_id}")],
            [InlineKeyboardButton("✏️ Сменить предпочтения", callback_data=f"change_prefs_{record_id}")],
            [InlineKeyboardButton("❌ Пропустить", callback_data="skip_gift")]
        ]
        await update.message.reply_text(f"🎁 Варианты подарков:\n\n{suggestions}\n\nВыберите:", reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END
 
async def select_gift_callback(update, context):
    query = update.callback_query
    await query.answer()
    gift_number = int(query.data.split("_")[2])
    gifts = context.user_data.get('current_gifts', [])
    record_id = context.user_data.get('current_record_id')
    result = call_api('get_or_create_user', {'username': update.effective_user.username or update.effective_user.first_name})
    user_id = result.get('user_id') if result else None
    selected = next((g['text'] for g in gifts if g['number'] == gift_number), None)
    if selected and record_id and user_id:
        call_api('update_gift', {'record_id': record_id, 'user_id': user_id, 'what_gift': f"🎁 {selected}"})
        await query.edit_message_text(f"✅ Выбран подарок:\n\n{selected}\n\n💾 Сохранён в /my_dates")
    return ConversationHandler.END
 
async def gift_action_callback(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data
    record_id = context.user_data.get('current_record_id')
    if data.startswith("find_more_"):
        rid = int(data.split("_")[2])
        preferences = context.user_data.get('current_preferences', '')
        if preferences:
            msg = await query.edit_message_text("🔄 Генерирую новые варианты...")
            new_sugg = get_gift_suggestions(preferences)
            await msg.delete()
            gifts = parse_gift_suggestions(new_sugg)
            context.user_data['current_gifts'] = gifts
            keyboard = [[InlineKeyboardButton(f"🎁 Выбрать вариант {g['number']}", callback_data=f"select_gift_{g['number']}")] for g in gifts]
            keyboard += [
                [InlineKeyboardButton("🔄 Найти другие", callback_data=f"find_more_{rid}")],
                [InlineKeyboardButton("✏️ Сменить предпочтения", callback_data=f"change_prefs_{rid}")],
                [InlineKeyboardButton("❌ Пропустить", callback_data="skip_gift")]
            ]
            await query.edit_message_text(f"🎁 Другие варианты:\n\n{new_sugg}\n\nВыберите:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith("change_prefs_"):
        context.user_data['changing_prefs_record'] = int(data.split("_")[2])
        await query.edit_message_text("✏️ Напишите новые предпочтения:")
        return WAITING_PREFERENCES
    elif data == "skip_gift":
        await query.edit_message_text("✅ Дата сохранена без подарка.")
        return ConversationHandler.END
    return ConversationHandler.END
 
async def receive_new_preferences(update, context):
    new_prefs = update.message.text
    result = call_api('get_or_create_user', {'username': update.effective_user.username or update.effective_user.first_name})
    user_id = result.get('user_id') if result else None
    record_id = context.user_data.get('changing_prefs_record')
    if user_id and record_id:
        call_api('update_preferences', {'record_id': record_id, 'user_id': user_id, 'preferences': new_prefs})
        msg = await update.message.reply_text("🔄 Генерирую варианты...")
        suggestions = get_gift_suggestions(new_prefs)
        await msg.delete()
        gifts = parse_gift_suggestions(suggestions)
        context.user_data.update({'current_gifts': gifts, 'current_preferences': new_prefs, 'current_record_id': record_id})
        keyboard = [[InlineKeyboardButton(f"🎁 Выбрать вариант {g['number']}", callback_data=f"select_gift_{g['number']}")] for g in gifts]
        keyboard += [
            [InlineKeyboardButton("🔄 Найти другие", callback_data=f"find_more_{record_id}")],
            [InlineKeyboardButton("✏️ Сменить предпочтения", callback_data=f"change_prefs_{record_id}")],
            [InlineKeyboardButton("❌ Пропустить", callback_data="skip_gift")]
        ]
        await update.message.reply_text(f"🎁 Новые варианты:\n\n{suggestions}\n\nВыберите:", reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END
 
async def reminder_callback(update, context):
    query = update.callback_query
    await query.answer()
    if query.data == "add_reminder":
        await query.edit_message_text("📝 Напишите текст напоминания:")
        return CHOOSING_REMINDER
    elif query.data == "no_reminder":
        result = call_api('get_or_create_user', {'username': update.effective_user.username or update.effective_user.first_name})
        user_id = result.get('user_id') if result else None
        if user_id:
            y, m, d = context.user_data.get('selected_year'), context.user_data.get('selected_month'), context.user_data.get('selected_day')
            save_result = call_api('save_user_date', {'user_id': user_id, 'year': y, 'month': m, 'day': d, 'holiday_reminder': None})
            if save_result and save_result.get('record_id'):
                record_id = save_result['record_id']
                context.user_data['last_record_id'] = record_id
                count_result = call_api('get_user_dates', {'user_id': user_id})
                total = count_result.get('count', 0) if count_result else 0
                keyboard = [
                    [InlineKeyboardButton("🎁 Да, помоги подобрать подарок", callback_data="need_gift_help")],
                    [InlineKeyboardButton("❌ Нет, просто сохранить дату", callback_data="no_gift_help")]
                ]
                await query.edit_message_text(
                    f"✅ Дата {d}.{m}.{y} сохранена!\n\n📊 Всего дат: {total}\n\nПомочь с подарком?",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
    return ConversationHandler.END
 
async def receive_reminder(update, context):
    reminder_text = update.message.text.strip()
    if not reminder_text:
        await update.message.reply_text("Напишите текст напоминания:")
        return CHOOSING_REMINDER
    result = call_api('get_or_create_user', {'username': update.effective_user.username or update.effective_user.first_name})
    user_id = result.get('user_id') if result else None
    if user_id:
        y, m, d = context.user_data.get('selected_year'), context.user_data.get('selected_month'), context.user_data.get('selected_day')
        save_result = call_api('save_user_date', {'user_id': user_id, 'year': y, 'month': m, 'day': d, 'holiday_reminder': reminder_text})
        if save_result and save_result.get('record_id'):
            record_id = save_result['record_id']
            context.user_data['last_record_id'] = record_id
            count_result = call_api('get_user_dates', {'user_id': user_id})
            total = count_result.get('count', 0) if count_result else 0
            keyboard = [
                [InlineKeyboardButton("🎁 Да, помоги подобрать подарок", callback_data="need_gift_help")],
                [InlineKeyboardButton("❌ Нет, просто сохранить дату", callback_data="no_gift_help")]
            ]
            await update.message.reply_text(
                f"✅ Дата {d}.{m}.{y}\n📌 Напоминание: {reminder_text}\n\n📊 Всего дат: {total}\n\nПомочь с подарком?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    return ConversationHandler.END
 
async def button_callback(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "ignore":
        return
    elif data in ("show_calendar", "today"):
        now = datetime.now()
        await query.edit_message_text("📆 Выберите дату:", reply_markup=create_calendar(now.year, now.month))
    elif data.startswith("nav_"):
        _, year, month = data.split("_")
        await query.edit_message_text("📆 Выберите дату:", reply_markup=create_calendar(int(year), int(month)))
    elif data.startswith("date_"):
        _, year, month, day = data.split("_")
        context.user_data.update({'selected_year': int(year), 'selected_month': int(month), 'selected_day': int(day)})
        keyboard = [
            [InlineKeyboardButton("✅ Да, добавить напоминание", callback_data="add_reminder")],
            [InlineKeyboardButton("❌ Нет, не нужно", callback_data="no_reminder")]
        ]
        await query.edit_message_text(
            f"📅 Вы выбрали: {day}.{month}.{year}\n\nДобавить напоминание?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif data == "close":
        await query.edit_message_text("❌ Календарь закрыт")
 
async def handle_message(update, context):
    keyboard = [[InlineKeyboardButton("📅 Выбрать дату", callback_data='show_calendar')]]
    await update.message.reply_text(
        random.choice(["Привет! 😊", "Здравствуй! 🌟", "Привет-привет! 🎈"]),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
 
async def error_handler(update, context):
    logger.error(f"Ошибка: {context.error}")
 
def main():
    print("=" * 50)
    print("🤖 Запускаю Telegram бота...")
    
    # Проверяем доступность Flask API
    if not check_api_available():
        print("⚠️ ВНИМАНИЕ: Flask API недоступен!")
        print(f"⚠️ Убедитесь, что Flask сервер запущен на {API_BASE_URL}")
        print("⚠️ Запустите flask_api.py в отдельном терминале")
        response = input("Продолжить запуск бота? (y/n): ")
        if response.lower() != 'y':
            return
    
    app = Application.builder().token(TOKEN).build()
 
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("hello", hello_command))
    app.add_handler(CommandHandler("choose_date", choose_date_command))
    app.add_handler(CommandHandler("my_dates", my_dates_command))
    app.add_handler(CallbackQueryHandler(select_gift_callback, pattern="^select_gift_"))
 
    gift_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(gift_choice_callback, pattern="^(need_gift_help|no_gift_help)$")],
        states={WAITING_PREFERENCES: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_preferences)]},
        fallbacks=[CommandHandler("cancel", lambda u,c: u.message.reply_text("Отменено"))],
    )
    reminder_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(reminder_callback, pattern="^(add_reminder|no_reminder)$")],
        states={CHOOSING_REMINDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_reminder)]},
        fallbacks=[CommandHandler("cancel", lambda u,c: u.message.reply_text("Отменено"))],
    )
    change_prefs_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(gift_action_callback, pattern="^change_prefs_")],
        states={WAITING_PREFERENCES: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_preferences)]},
        fallbacks=[CommandHandler("cancel", lambda u,c: u.message.reply_text("Отменено"))],
    )
 
    app.add_handler(CallbackQueryHandler(button_callback, pattern="^(?!need_gift_help|no_gift_help|add_reminder|no_reminder|find_more_|change_prefs_|select_gift_|skip_gift).*"))
    app.add_handler(CallbackQueryHandler(gift_action_callback, pattern="^(find_more_|skip_gift)"))
    app.add_handler(reminder_conv_handler)
    app.add_handler(gift_conv_handler)
    app.add_handler(change_prefs_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
 
    print("✅ Telegram бот запущен!")
    app.run_polling(allowed_updates=['message', 'callback_query'], drop_pending_updates=True, timeout=30)
 
if __name__ == "__main__":
    main()
