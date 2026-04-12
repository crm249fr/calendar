from flask import Flask, request, jsonify
from flask_cors import CORS
from Database import (
    init_database, get_or_create_user, save_user_date, 
    update_gift_for_record, update_preferences_for_record,
    get_user_dates, get_user_dates_count, get_last_record_id,
    get_last_preferences
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Разрешаем кросс-доменные запросы

# Инициализация БД при старте
init_database()

@app.route('/api/get_or_create_user', methods=['POST'])
def api_get_or_create_user():
    try:
        data = request.json
        username = data.get('username')
        if not username:
            return jsonify({'error': 'username required'}), 400
        user_id = get_or_create_user(username)
        return jsonify({'user_id': user_id})
    except Exception as e:
        logger.error(f"Error in get_or_create_user: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/save_user_date', methods=['POST'])
def api_save_user_date():
    try:
        data = request.json
        required = ['user_id', 'year', 'month', 'day']
        if not all(k in data for k in required):
            return jsonify({'error': 'Missing required fields'}), 400
        record_id = save_user_date(
            data['user_id'], data['year'], data['month'], data['day'],
            data.get('event'), data.get('whom'), 
            data.get('what_gift'), data.get('holiday_reminder')
        )
        return jsonify({'record_id': record_id})
    except Exception as e:
        logger.error(f"Error in save_user_date: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/update_gift', methods=['POST'])
def api_update_gift():
    try:
        data = request.json
        if not all(k in data for k in ['record_id', 'user_id', 'what_gift']):
            return jsonify({'error': 'Missing required fields'}), 400
        success = update_gift_for_record(data['record_id'], data['user_id'], data['what_gift'])
        return jsonify({'success': success})
    except Exception as e:
        logger.error(f"Error in update_gift: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/update_preferences', methods=['POST'])
def api_update_preferences():
    try:
        data = request.json
        if not all(k in data for k in ['record_id', 'user_id', 'preferences']):
            return jsonify({'error': 'Missing required fields'}), 400
        success = update_preferences_for_record(data['record_id'], data['user_id'], data['preferences'])
        return jsonify({'success': success})
    except Exception as e:
        logger.error(f"Error in update_preferences: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/get_user_dates', methods=['POST'])
def api_get_user_dates():
    try:
        data = request.json
        user_id = data.get('user_id')
        limit = data.get('limit', 5)
        if not user_id:
            return jsonify({'error': 'user_id required'}), 400
        dates = get_user_dates(user_id, limit)
        count = get_user_dates_count(user_id)
        return jsonify({'dates': dates, 'count': count})
    except Exception as e:
        logger.error(f"Error in get_user_dates: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/get_last_record_id', methods=['POST'])
def api_get_last_record_id():
    try:
        data = request.json
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id required'}), 400
        record_id = get_last_record_id(user_id)
        return jsonify({'record_id': record_id})
    except Exception as e:
        logger.error(f"Error in get_last_record_id: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/get_last_preferences', methods=['POST'])
def api_get_last_preferences():
    try:
        data = request.json
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id required'}), 400
        preferences = get_last_preferences(user_id)
        return jsonify({'preferences': preferences})
    except Exception as e:
        logger.error(f"Error in get_last_preferences: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    from API import API_HOST, API_PORT
    print(f"🚀 Flask API запущен на http://{API_HOST}:{API_PORT}")
    app.run(host=API_HOST, port=API_PORT, debug=True)
