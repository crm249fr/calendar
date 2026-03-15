import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from datetime import datetime
import calendar
import random
import asyncio

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = "8765454976:AAGolrqZ8bcQJTj8FnCN1ltagpM0TBbNGDk"

user_dates = {}

MONTHS_RU = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
             'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']

def create_calendar(year: int, month: int):
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

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        
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
    try:
        user_id = update.effective_user.id
        
        if user_id in user_dates and user_dates[user_id]:
            dates_list = "\n".join([f"• {date}" for date in user_dates[user_id][-5:]])  # Показываем последние 5
            await update.message.reply_text(
                f"📅 Ваши последние даты:\n\n{dates_list}\n\n"
                f"Всего: {len(user_dates[user_id])}"
            )
        else:
            await update.message.reply_text("У вас пока нет сохраненных дат.")
    except Exception as e:
        logger.error(f"Ошибка в my_dates: {e}")

async def hello_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text("Привет! 🎉")
    except Exception as e:
        logger.error(f"Ошибка в hello: {e}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            
            # Сохраняем дату
            user_id = update.effective_user.id
            if user_id not in user_dates:
                user_dates[user_id] = []
            user_dates[user_id].append(selected_date)
            
            await query.edit_message_text(
                text=f"✅ Дата {selected_date} сохранена!\n"
                     f"Всего дат: {len(user_dates[user_id])}"
            )
            
            keyboard = [[InlineKeyboardButton("📅 Выбрать еще", callback_data='show_calendar')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text="Хотите выбрать еще дату?",
                reply_markup=reply_markup
            )
        
        elif data == "close":
            await query.edit_message_text(text="❌ Календарь закрыт")
    
    except Exception as e:
        logger.error(f"Ошибка в button_callback: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        responses = ["Привет! 😊", "Здравствуй! 🌟", "Привет-привет! 🎈"]
        response = random.choice(responses)
        
        keyboard = [[InlineKeyboardButton("📅 Выбрать дату", callback_data='show_calendar')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(response, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Ошибка в handle_message: {e}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("hello", hello_command))
    app.add_handler(CommandHandler("choose_date", choose_date_command))
    app.add_handler(CommandHandler("my_dates", my_dates_command))
    
    app.add_handler(CallbackQueryHandler(button_callback))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.add_error_handler(error_handler)
    
    print("✅ Бот запущен! Доступные команды: /start, /hello, /choose_date, /my_dates")
    print("⚠️ Нажмите Ctrl+C для остановки.")
    
    app.run_polling(
        allowed_updates=['message', 'callback_query'],
        drop_pending_updates=True,
        timeout=30
    )

if __name__ == "__main__":
    main()
