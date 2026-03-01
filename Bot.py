import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = "8319493214:AAH7OER2ucuTTyvpDDjmppU-X3qUvwuRyoA"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отвечает только на команду старт"""
    user = update.effective_user
    
    await update.message.reply_text(
        f"Привет, {user.first_name}! 👋\n"
        "Я бот, который поможет тебе ничего не забывать\n"
    )
    
    logger.info(f"Пользователь {user.first_name} (ID: {user.id}) запустил бота")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Логирует ошибки"""
    logger.error(f"Ошибка: {context.error}")

def main():
    """Главная функция"""
    print("🚀 Запускаю бота...")
    print("📝 Бот будет реагировать только на команду /start")
    print("⚠️ Нажмите Ctrl+C для остановки")
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    
    app.add_error_handler(error_handler)
    
    app.run_polling(allowed_updates=['message'])

if __name__ == "__main__":
    main()