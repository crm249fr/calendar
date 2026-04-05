import subprocess
import sys
import time
import os

def run_api_server():
    """Запуск Flask API сервера"""
    print("🚀 Запуск API сервера...")
    api_process = subprocess.Popen([sys.executable, "database_api.py"])
    return api_process

def run_bot():
    """Запуск Telegram бота"""
    print("🤖 Запуск Telegram бота...")
    bot_process = subprocess.Popen([sys.executable, "Bot.py"])
    return bot_process

if __name__ == "__main__":
    print("=" * 50)
    print("Запуск системы SmartNotes")
    print("=" * 50)
    
    # Запускаем API сервер
    api_process = run_api_server()
    time.sleep(3)  # Ждем запуска сервера
    
    # Запускаем бота
    bot_process = run_bot()
    
    print("\n✅ Система запущена!")
    print("Нажмите Ctrl+C для остановки всех процессов\n")
    
    try:
        # Ждем завершения процессов
        api_process.wait()
        bot_process.wait()
    except KeyboardInterrupt:
        print("\n\n⚠️ Остановка системы...")
        api_process.terminate()
        bot_process.terminate()
        print("✅ Система остановлена")