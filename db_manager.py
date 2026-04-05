from database import db
from database.models import User, UserDate
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    
    @staticmethod
    def init_db():
        """Инициализация базы данных"""
        db.create_all()
        logger.info("База данных инициализирована")
    
    @staticmethod
    def get_or_create_user(username):
        """Получить или создать пользователя"""
        try:
            user = User.get_or_create(username)
            return user.id
        except Exception as e:
            logger.error(f"Ошибка при получении/создании пользователя: {e}")
            return None
    
    @staticmethod
    def save_user_date(user_id, year, month, day, event=None, whom=None, what_gift=None):
        """Сохранить дату пользователя"""
        try:
            user_date = UserDate(
                user_id=user_id,
                year=year,
                month=month,
                day=day,
                event=event,
                whom=whom,
                what_gift=what_gift
            )
            db.session.add(user_date)
            db.session.commit()
            logger.info(f"Дата {day}.{month}.{year} сохранена для пользователя {user_id}")
            return user_date.id
        except Exception as e:
            logger.error(f"Ошибка при сохранении даты: {e}")
            db.session.rollback()
            return None
    
    @staticmethod
    def update_gift_for_record(record_id, user_id, what_gift):
        """Обновить подарок для записи"""
        try:
            user_date = UserDate.query.filter_by(id=record_id, user_id=user_id).first()
            if user_date:
                user_date.what_gift = what_gift
                db.session.commit()
                logger.info(f"Подарок сохранен для записи {record_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка при обновлении подарка: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def update_preferences_for_record(record_id, user_id, preferences):
        """Обновить предпочтения для записи"""
        try:
            user_date = UserDate.query.filter_by(id=record_id, user_id=user_id).first()
            if user_date:
                user_date.preferences = preferences
                db.session.commit()
                logger.info(f"Предпочтения сохранены для записи {record_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка при обновлении предпочтений: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def get_user_dates(user_id, limit=5):
        """Получить последние даты пользователя"""
        try:
            dates = UserDate.query.filter_by(user_id=user_id)\
                .order_by(UserDate.id.desc())\
                .limit(limit)\
                .all()
            return [date.to_short_dict() for date in dates]
        except Exception as e:
            logger.error(f"Ошибка при получении дат: {e}")
            return []
    
    @staticmethod
    def get_user_dates_count(user_id):
        """Получить количество дат пользователя"""
        try:
            return UserDate.query.filter_by(user_id=user_id).count()
        except Exception as e:
            logger.error(f"Ошибка при подсчете дат: {e}")
            return 0
    
    @staticmethod
    def get_last_record_id(user_id):
        """Получить ID последней записи"""
        try:
            last_date = UserDate.query.filter_by(user_id=user_id)\
                .order_by(UserDate.id.desc())\
                .first()
            return last_date.id if last_date else None
        except Exception as e:
            logger.error(f"Ошибка при получении последней записи: {e}")
            return None
    
    @staticmethod
    def get_last_preferences(user_id):
        """Получить предпочтения из последней записи"""
        try:
            last_date = UserDate.query.filter_by(user_id=user_id)\
                .order_by(UserDate.id.desc())\
                .first()
            return last_date.preferences if last_date and last_date.preferences else None
        except Exception as e:
            logger.error(f"Ошибка при получении предпочтений: {e}")
            return None
