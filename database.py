"""
Модуль работы с базой данных для системы СКУД
"""
import sqlite3
import datetime
import logging
from config import DB_PATH, DEFAULT_ZONES, PASS_VALID_SECONDS

logger = logging.getLogger(__name__)


def get_connection():
    """Получить соединение с базой данных"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Инициализация базы данных - создание таблиц и индексов"""
    conn = get_connection()
    cursor = conn.cursor()

    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            uid TEXT PRIMARY KEY,
            rank INTEGER NOT NULL,
            secret_key TEXT NOT NULL,
            current_zone INTEGER NOT NULL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Таблица зон
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS zones (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            is_exit INTEGER NOT NULL DEFAULT 0,
            required_rank INTEGER NOT NULL DEFAULT 3
        )
    ''')

    # Журнал проходов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS access_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid TEXT NOT NULL,
            zone_from INTEGER NOT NULL,
            zone_to INTEGER NOT NULL,
            success INTEGER NOT NULL,
            reason TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (uid) REFERENCES users(uid)
        )
    ''')

    # Таблица блокировок
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS access_blocks (
            uid TEXT PRIMARY KEY,
            fail_count INTEGER NOT NULL DEFAULT 0,
            blocked_until DATETIME,
            FOREIGN KEY (uid) REFERENCES users(uid)
        )
    ''')

    # Таблица временных сессий
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pending_passes (
            uid TEXT PRIMARY KEY,
            zone_from INTEGER NOT NULL,
            zone_to INTEGER NOT NULL,
            authorized_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (uid) REFERENCES users(uid)
        )
    ''')

    # Таблица истории перемещений пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid TEXT NOT NULL,
            zone_id INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (uid) REFERENCES users(uid),
            FOREIGN KEY (zone_id) REFERENCES zones(id)
        )
    ''')

    # Создаём индексы для ускорения выборки
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_access_logs_uid ON access_logs(uid)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_access_logs_timestamp ON access_logs(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_access_logs_uid_timestamp ON access_logs(uid, timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_history_uid ON user_history(uid)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_history_timestamp ON user_history(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_pending_passes_authorized_at ON pending_passes(authorized_at)')

    # Базовые зоны
    cursor.executemany(
        "INSERT OR IGNORE INTO zones (id, name, is_exit, required_rank) VALUES (?, ?, ?, ?)",
        DEFAULT_ZONES
    )

    conn.commit()
    conn.close()
    logger.info("База данных инициализирована")


def add_user(uid: str, rank: int, secret_key: bytes, current_zone: int = 0):
    """Добавить или обновить пользователя"""
    conn = get_connection()
    cursor = conn.cursor()
    # Сохраняем ключ как hex-строку
    secret_key_hex = secret_key.hex() if isinstance(secret_key, bytes) else secret_key
    cursor.execute(
        "INSERT OR REPLACE INTO users (uid, rank, secret_key, current_zone) VALUES (?, ?, ?, ?)",
        (uid, rank, secret_key_hex, current_zone)
    )
    conn.commit()
    conn.close()
    logger.info(f"Пользователь {uid} добавлен с рангом {rank}")


def get_user(uid: str):
    """Получить пользователя по UID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE uid = ?", (uid,))
    user = cursor.fetchone()
    conn.close()
    return user


def get_user_current_zone(uid: str) -> int:
    """Получить текущую зону пользователя"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT current_zone FROM users WHERE uid = ?", (uid,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0


def update_user_current_zone(uid: str, zone_id: int):
    """Обновить текущую зону пользователя"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET current_zone = ? WHERE uid = ?", (zone_id, uid))
    conn.commit()
    conn.close()
    logger.debug(f"Пользователь {uid} перемещён в зону {zone_id}")


def add_to_history(uid: str, zone_id: int):
    """Добавить запись в историю перемещений"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO user_history (uid, zone_id) VALUES (?, ?)",
        (uid, zone_id)
    )
    conn.commit()
    conn.close()
    logger.debug(f"Добавлена история для {uid}: зона {zone_id}")


def get_user_history(uid: str, limit: int = 10) -> list:
    """Получить историю перемещений пользователя"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT zone_id, timestamp FROM user_history WHERE uid = ? ORDER BY timestamp DESC LIMIT ?",
        (uid, limit)
    )
    history = [row['zone_id'] for row in cursor.fetchall()]
    conn.close()
    return list(reversed(history))  # Возвращаем в хронологическом порядке


def log_access(uid: str, zone_from: int, zone_to: int, success: bool, reason: str = ""):
    """Записать событие доступа в журнал"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO access_logs (uid, zone_from, zone_to, success, reason) VALUES (?, ?, ?, ?, ?)",
        (uid, zone_from, zone_to, int(success), reason)
    )
    conn.commit()
    conn.close()
    logger.info(f"Доступ: {uid} {zone_from}→{zone_to} {'✅' if success else '❌'} {reason}")


def get_zones_info():
    """Получить информацию обо всех зонах"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, is_exit, required_rank FROM zones")
    zones = {
        row['id']: {
            'name': row['name'],
            'is_exit': bool(row['is_exit']),
            'required_rank': row['required_rank']
        }
        for row in cursor.fetchall()
    }
    conn.close()
    return zones


def check_block(uid: str):
    """Проверить, заблокирован ли пользователь"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT fail_count, blocked_until FROM access_blocks WHERE uid = ?", (uid,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return False, 0
    
    fail_count, blocked_until = row
    if blocked_until:
        blocked_time = datetime.datetime.fromisoformat(blocked_until)
        if datetime.datetime.now() < blocked_time:
            return True, fail_count
    
    return False, fail_count


def increment_fail(uid: str):
    """Увеличить счётчик неудачных попыток"""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now()
    blocked_until = now + datetime.timedelta(minutes=1)
    is_blocked, fail_count = check_block(uid)
    new_count = fail_count + 1
    
    if new_count >= 3:
        cursor.execute('''
            INSERT OR REPLACE INTO access_blocks (uid, fail_count, blocked_until)
            VALUES (?, ?, ?)
        ''', (uid, new_count, blocked_until.isoformat()))
        conn.commit()
        conn.close()
        logger.warning(f"Пользователь {uid} заблокирован на 1 минуту")
        return True, blocked_until
    else:
        cursor.execute('''
            INSERT OR REPLACE INTO access_blocks (uid, fail_count, blocked_until)
            VALUES (?, ?, NULL)
        ''', (uid, new_count))
        conn.commit()
        conn.close()
        return False, None


def reset_fail(uid: str):
    """Сбросить счётчик неудачных попыток"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM access_blocks WHERE uid = ?", (uid,))
    conn.commit()
    conn.close()
    logger.debug(f"Сброшены неудачные попытки для {uid}")


def create_pending_pass(uid: str, zone_from: int, zone_to: int):
    """Создать временную сессию прохода"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO pending_passes (uid, zone_from, zone_to)
        VALUES (?, ?, ?)
    ''', (uid, zone_from, zone_to))
    conn.commit()
    conn.close()
    logger.debug(f"Создан временный проход для {uid}: {zone_from}→{zone_to}")


def confirm_pass(uid: str) -> bool:
    """
    Подтвердить проход пользователя.
    Использует транзакцию с блокировкой для предотвращения гонки условий.
    """
    conn = get_connection()
    try:
        # Начинаем транзакцию с немедленной блокировкой
        conn.execute("BEGIN IMMEDIATE")
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM pending_passes WHERE uid = ?", (uid,))
        pass_data = cursor.fetchone()
        
        if not pass_data:
            conn.rollback()
            logger.warning(f"Попытка подтвердить несуществующий проход для {uid}")
            raise ValueError("Временный проход не найден")
        
        uid_val, zone_from, zone_to, _ = pass_data
        
        # Обновляем текущую зону
        cursor.execute("UPDATE users SET current_zone = ? WHERE uid = ?", (zone_to, uid))
        
        # Записываем в журнал
        cursor.execute(
            "INSERT INTO access_logs (uid, zone_from, zone_to, success, reason) VALUES (?, ?, ?, ?, ?)",
            (uid, zone_from, zone_to, 1, "Проход подтверждён")
        )
        
        # Добавляем в историю перемещений
        cursor.execute(
            "INSERT INTO user_history (uid, zone_id) VALUES (?, ?)",
            (uid, zone_to)
        )
        
        # Удаляем временную сессию
        cursor.execute("DELETE FROM pending_passes WHERE uid = ?", (uid,))
        
        # Сбрасываем счётчик неудачных попыток
        cursor.execute("DELETE FROM access_blocks WHERE uid = ?", (uid,))
        
        conn.commit()
        logger.info(f"Проход подтверждён: {uid} {zone_from}→{zone_to}")
        return True
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Ошибка подтверждения прохода: {e}")
        raise
    finally:
        conn.close()


def cleanup_expired_passes():
    """Удалить просроченные временные сессии"""
    conn = get_connection()
    cursor = conn.cursor()
    # SQLite не поддерживает параметры внутри строковых литералов,
    # поэтому используем вычисление времени напрямую
    cursor.execute(f'''
        DELETE FROM pending_passes
        WHERE datetime(authorized_at) < datetime('now', '-{PASS_VALID_SECONDS} seconds')
    ''')
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    if deleted_count > 0:
        logger.debug(f"Удалено {deleted_count} просроченных сессий")


def get_pending_pass(uid: str):
    """Получить временную сессию по UID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pending_passes WHERE uid = ?", (uid,))
    pass_data = cursor.fetchone()
    conn.close()
    return pass_data


def get_all_users():
    """Получить всех пользователей"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT uid, rank, current_zone, created_at FROM users ORDER BY uid")
    users = cursor.fetchall()
    conn.close()
    return users


def get_recent_logs(limit: int = 100):
    """Получить последние записи журнала"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM access_logs ORDER BY timestamp DESC LIMIT ?",
        (limit,)
    )
    logs = cursor.fetchall()
    conn.close()
    return logs


def delete_user(uid: str) -> bool:
    """
    Удалить пользователя по UID.
    Возвращает True если пользователь удалён, False если не найден.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE uid = ?", (uid,))
    deleted = cursor.rowcount > 0
    # Также удаляем связанные записи
    cursor.execute("DELETE FROM access_blocks WHERE uid = ?", (uid,))
    cursor.execute("DELETE FROM pending_passes WHERE uid = ?", (uid,))
    cursor.execute("DELETE FROM user_history WHERE uid = ?", (uid,))
    conn.commit()
    conn.close()
    if deleted:
        logger.info(f"Пользователь {uid} удалён")
    return deleted


def update_user(uid: str, rank: int = None, name: str = None, current_zone: int = None) -> bool:
    """
    Обновить данные пользователя.
    Возвращает True если пользователь обновлён, False если не найден.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Проверяем существование пользователя
    cursor.execute("SELECT uid FROM users WHERE uid = ?", (uid,))
    if not cursor.fetchone():
        conn.close()
        logger.warning(f"Попытка обновить несуществующего пользователя {uid}")
        return False
    
    updates = []
    values = []
    
    if rank is not None:
        updates.append("rank = ?")
        values.append(rank)
    
    if current_zone is not None:
        updates.append("current_zone = ?")
        values.append(current_zone)
    
    if updates:
        values.append(uid)
        query = f"UPDATE users SET {', '.join(updates)} WHERE uid = ?"
        cursor.execute(query, values)
        conn.commit()
        logger.info(f"Пользователь {uid} обновлён")
    
    conn.close()
    return True


def get_user_by_uid(uid: str):
    """Получить пользователя по UID (полная информация)"""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE uid = ?", (uid,))
    user = cursor.fetchone()
    conn.close()
    return user


def get_users_with_zones():
    """Получить всех пользователей с указанием их текущих зон"""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.uid, u.rank, u.current_zone, u.created_at, z.name as zone_name
        FROM users u
        LEFT JOIN zones z ON u.current_zone = z.id
        ORDER BY u.uid
    ''')
    users = cursor.fetchall()
    conn.close()
    return users


def get_zone_users(zone_id: int):
    """Получить всех пользователей в указанной зоне"""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT uid, rank, current_zone FROM users WHERE current_zone = ? ORDER BY uid",
        (zone_id,)
    )
    users = cursor.fetchall()
    conn.close()
    return users


# При первом импорте инициализируем БД
init_db()
