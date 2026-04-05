from flask import Flask, request, jsonify
from flask_restful import Api, Resource
import sqlite3
import logging
from datetime import datetime

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
api = Api(app)

def init_database():
    """Инициализация базы данных"""
    try:
        conn = sqlite3.connect('smartnotes.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        logger.info("База данных успешно инициализирована")
        return conn
        
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        return None

def create_user_table(user_id):
    """Создает таблицу для пользователя"""
    conn = None
    try:
        conn = sqlite3.connect('smartnotes.db')
        cursor = conn.cursor()
        
        cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS "user_{user_id}" (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                day INTEGER NOT NULL,
                time TEXT,
                event TEXT,
                whom TEXT,
                what_gift TEXT,
                preferences TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        logger.info(f"Создана таблица для пользователя с ID {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при создании таблицы пользователя: {e}")
        return False
    finally:
        if conn:
            conn.close()

class UserResource(Resource):
    """Ресурс для работы с пользователями"""
    
    def post(self):
        """Создание или получение пользователя"""
        try:
            data = request.get_json()
            username = data.get('username')
            
            if not username:
                return {'error': 'Username is required'}, 400
            
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
                
                # Создаем таблицу для пользователя
                create_user_table(user_id)
            
            conn.close()
            
            return {
                'user_id': user_id,
                'username': username,
                'is_new': not bool(result)
            }, 200
            
        except Exception as e:
            logger.error(f"Ошибка при получении/создании пользователя: {e}")
            return {'error': str(e)}, 500

class DateResource(Resource):
    """Ресурс для работы с датами"""
    
    def post(self, user_id):
        """Сохранение даты"""
        try:
            data = request.get_json()
            year = data.get('year')
            month = data.get('month')
            day = data.get('day')
            event = data.get('event')
            whom = data.get('whom')
            what_gift = data.get('what_gift')
            
            if not all([year, month, day]):
                return {'error': 'Year, month and day are required'}, 400
            
            conn = sqlite3.connect('smartnotes.db')
            cursor = conn.cursor()
            
            # Проверяем существование таблицы
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (f'user_{user_id}',))
            if not cursor.fetchone():
                create_user_table(user_id)
            
            cursor.execute(f'''
                INSERT INTO "user_{user_id}" (year, month, day, event, whom, what_gift)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (year, month, day, event, whom, what_gift))
            
            conn.commit()
            record_id = cursor.lastrowid
            conn.close()
            
            logger.info(f"Дата {day}.{month}.{year} сохранена для пользователя {user_id}")
            
            return {
                'record_id': record_id,
                'message': 'Date saved successfully'
            }, 201
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении даты: {e}")
            return {'error': str(e)}, 500
    
    def get(self, user_id):
        """Получение дат пользователя"""
        try:
            limit = request.args.get('limit', 5, type=int)
            
            conn = sqlite3.connect('smartnotes.db')
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (f'user_{user_id}',))
            if not cursor.fetchone():
                conn.close()
                return {'dates': [], 'count': 0}, 200
            
            cursor.execute(f'''
                SELECT id, year, month, day, what_gift, preferences, created_at
                FROM "user_{user_id}"
                ORDER BY id DESC
                LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            
            dates = []
            for row in rows:
                dates.append({
                    'id': row[0],
                    'year': row[1],
                    'month': row[2],
                    'day': row[3],
                    'what_gift': row[4],
                    'preferences': row[5],
                    'created_at': row[6]
                })
            
            cursor.execute(f'SELECT COUNT(*) FROM "user_{user_id}"')
            count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'dates': dates,
                'count': count
            }, 200
            
        except Exception as e:
            logger.error(f"Ошибка при получении дат: {e}")
            return {'error': str(e)}, 500

class GiftResource(Resource):
    """Ресурс для работы с подарками"""
    
    def put(self, user_id, record_id):
        """Обновление подарка"""
        try:
            data = request.get_json()
            what_gift = data.get('what_gift')
            
            if not what_gift:
                return {'error': 'what_gift is required'}, 400
            
            conn = sqlite3.connect('smartnotes.db')
            cursor = conn.cursor()
            
            cursor.execute(f'''
                UPDATE "user_{user_id}"
                SET what_gift = ?
                WHERE id = ?
            ''', (what_gift, record_id))
            
            conn.commit()
            affected_rows = cursor.rowcount
            conn.close()
            
            if affected_rows > 0:
                logger.info(f"Подарок сохранен для записи {record_id} пользователя {user_id}")
                return {'message': 'Gift updated successfully'}, 200
            else:
                return {'error': 'Record not found'}, 404
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении подарка: {e}")
            return {'error': str(e)}, 500

class PreferencesResource(Resource):
    """Ресурс для работы с предпочтениями"""
    
    def put(self, user_id, record_id):
        """Обновление предпочтений"""
        try:
            data = request.get_json()
            preferences = data.get('preferences')
            
            if not preferences:
                return {'error': 'preferences is required'}, 400
            
            conn = sqlite3.connect('smartnotes.db')
            cursor = conn.cursor()
            
            cursor.execute(f'''
                UPDATE "user_{user_id}"
                SET preferences = ?
                WHERE id = ?
            ''', (preferences, record_id))
            
            conn.commit()
            affected_rows = cursor.rowcount
            conn.close()
            
            if affected_rows > 0:
                logger.info(f"Предпочтения сохранены для записи {record_id}")
                return {'message': 'Preferences updated successfully'}, 200
            else:
                return {'error': 'Record not found'}, 404
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении предпочтений: {e}")
            return {'error': str(e)}, 500
    
    def get(self, user_id):
        """Получение последних предпочтений"""
        try:
            conn = sqlite3.connect('smartnotes.db')
            cursor = conn.cursor()
            
            cursor.execute(f'''
                SELECT preferences FROM "user_{user_id}"
                WHERE preferences IS NOT NULL
                ORDER BY id DESC
                LIMIT 1
            ''')
            
            result = cursor.fetchone()
            conn.close()
            
            return {
                'preferences': result[0] if result else None
            }, 200
            
        except Exception as e:
            logger.error(f"Ошибка при получении предпочтений: {e}")
            return {'error': str(e)}, 500

class RecordResource(Resource):
    """Ресурс для получения конкретной записи"""
    
    def get(self, user_id, record_id):
        """Получение записи по ID"""
        try:
            conn = sqlite3.connect('smartnotes.db')
            cursor = conn.cursor()
            
            cursor.execute(f'''
                SELECT id, year, month, day, what_gift, preferences
                FROM "user_{user_id}"
                WHERE id = ?
            ''', (record_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'id': result[0],
                    'year': result[1],
                    'month': result[2],
                    'day': result[3],
                    'what_gift': result[4],
                    'preferences': result[5]
                }, 200
            else:
                return {'error': 'Record not found'}, 404
            
        except Exception as e:
            logger.error(f"Ошибка при получении записи: {e}")
            return {'error': str(e)}, 500

class StatsResource(Resource):
    """Ресурс для получения статистики"""
    
    def get(self, user_id):
        """Получение статистики пользователя"""
        try:
            conn = sqlite3.connect('smartnotes.db')
            cursor = conn.cursor()
            
            # Общее количество записей
            cursor.execute(f'SELECT COUNT(*) FROM "user_{user_id}"')
            total = cursor.fetchone()[0]
            
            # Количество записей с подарками
            cursor.execute(f'SELECT COUNT(*) FROM "user_{user_id}" WHERE what_gift IS NOT NULL')
            with_gifts = cursor.fetchone()[0]
            
            # Количество записей с предпочтениями
            cursor.execute(f'SELECT COUNT(*) FROM "user_{user_id}" WHERE preferences IS NOT NULL')
            with_preferences = cursor.fetchone()[0]
            
            # Даты по месяцам
            cursor.execute(f'''
                SELECT month, COUNT(*) 
                FROM "user_{user_id}" 
                GROUP BY month 
                ORDER BY month
            ''')
            monthly_stats = cursor.fetchall()
            
            conn.close()
            
            return {
                'total_dates': total,
                'dates_with_gifts': with_gifts,
                'dates_with_preferences': with_preferences,
                'monthly_distribution': [{'month': m, 'count': c} for m, c in monthly_stats]
            }, 200
            
        except Exception as e:
            logger.error(f"Ошибка при получении статистики: {e}")
            return {'error': str(e)}, 500

# Добавляем ресурсы в API
api.add_resource(UserResource, '/api/users')
api.add_resource(DateResource, '/api/users/<int:user_id>/dates')
api.add_resource(GiftResource, '/api/users/<int:user_id>/dates/<int:record_id>/gift')
api.add_resource(PreferencesResource, '/api/users/<int:user_id>/dates/<int:record_id>/preferences')
api.add_resource(PreferencesResource, '/api/users/<int:user_id>/preferences', endpoint='user_preferences')
api.add_resource(RecordResource, '/api/users/<int:user_id>/records/<int:record_id>')
api.add_resource(StatsResource, '/api/users/<int:user_id>/stats')

if __name__ == '__main__':
    # Инициализируем базу данных
    init_database()
    
    print("🚀 Запуск Flask-RESTful API сервера...")
    print(f"📍 API доступен по адресу: http://{API_HOST}:{API_PORT}")
    print("📋 Доступные эндпоинты:")
    print("  POST   /api/users                                    - Создать/получить пользователя")
    print("  POST   /api/users/<user_id>/dates                    - Сохранить дату")
    print("  GET    /api/users/<user_id>/dates?limit=N            - Получить даты")
    print("  PUT    /api/users/<user_id>/dates/<record_id>/gift    - Обновить подарок")
    print("  PUT    /api/users/<user_id>/dates/<record_id>/preferences - Обновить предпочтения")
    print("  GET    /api/users/<user_id>/preferences              - Получить последние предпочтения")
    print("  GET    /api/users/<user_id>/records/<record_id>      - Получить запись")
    print("  GET    /api/users/<user_id>/stats                    - Получить статистику")
    print("⚠️  Нажмите Ctrl+C для остановки")
    
    app.run(host=API_HOST, port=API_PORT, debug=False, threaded=True)