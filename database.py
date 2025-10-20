# database.py
import sqlite3
import os

DB_PATH = "skud.db"

def init_db():
    """Создаёт таблицы с поддержкой required_rank для зон."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            uid TEXT PRIMARY KEY,
            rank INTEGER NOT NULL,
            secret_key BLOB NOT NULL
        )
    ''')
    
    # Таблица зон с требуемым рангом
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS zones (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            is_exit INTEGER NOT NULL DEFAULT 0,
            required_rank INTEGER NOT NULL DEFAULT 3
        )
    ''')
    
    # Журнал проходов с причиной
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS access_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uid TEXT NOT NULL,
            zone_from INTEGER NOT NULL,
            zone_to INTEGER NOT NULL,
            success INTEGER NOT NULL,
            reason TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS access_blocks (
            uid TEXT PRIMARY KEY,
            fail_count INTEGER NOT NULL DEFAULT 0,
            blocked_until DATETIME
        )
    ''')

    # Базовые зоны (используем INSERT OR IGNORE, чтобы не дублировать)
    zones = [
        (0, 'Вход', 0, 3),
        (1, 'Офис', 0, 5),
        (2, 'Серверная', 0, 8),
        (999, 'Выход', 1, 3)
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO zones (id, name, is_exit, required_rank) VALUES (?, ?, ?, ?)",
        zones
    )
    
    conn.commit()
    conn.close()

def add_user(uid: str, rank: int, secret_key: bytes):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO users (uid, rank, secret_key) VALUES (?, ?, ?)",
        (uid, rank, secret_key)
    )
    conn.commit()
    conn.close()

def get_user(uid: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE uid = ?", (uid,))
    user = cursor.fetchone()
    conn.close()
    return user

def log_access(uid: str, zone_from: int, zone_to: int, success: bool, reason: str = ""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO access_logs (uid, zone_from, zone_to, success, reason) VALUES (?, ?, ?, ?, ?)",
        (uid, zone_from, zone_to, int(success), reason)
    )
    conn.commit()
    conn.close()

def get_zones_info():
    """Возвращает словарь: {id_зоны: {is_exit, required_rank}}"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, is_exit, required_rank FROM zones")
    zones = {
        row['id']: {
            'is_exit': bool(row['is_exit']),
            'required_rank': row['required_rank']
        }
        for row in cursor.fetchall()
    }
    conn.close()
    return zones
import datetime

def check_block(uid: str):
    """Проверяет, заблокирован ли пользователь."""
    conn = sqlite3.connect(DB_PATH)
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
            return True, fail_count  # Заблокирован
    
    return False, fail_count

def increment_fail(uid: str):
    """Увеличивает счётчик неудач и блокирует при необходимости."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.datetime.now()
    blocked_until = now + datetime.timedelta(minutes=1)
    
    is_blocked, fail_count = check_block(uid)
    new_count = fail_count + 1
    
    if new_count >= 3:
        # Блокируем на 1 минуту
        cursor.execute('''
            INSERT OR REPLACE INTO access_blocks (uid, fail_count, blocked_until)
            VALUES (?, ?, ?)
        ''', (uid, new_count, blocked_until.isoformat()))
        conn.commit()
        conn.close()
        return True, blocked_until
    else:
        # Обновляем счётчик
        cursor.execute('''
            INSERT OR REPLACE INTO access_blocks (uid, fail_count, blocked_until)
            VALUES (?, ?, NULL)
        ''', (uid, new_count))
        conn.commit()
        conn.close()
        return False, None

def reset_fail(uid: str):
    """Сбрасывает счётчик при успешной аутентификации."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM access_blocks WHERE uid = ?", (uid,))
    conn.commit()
    conn.close()