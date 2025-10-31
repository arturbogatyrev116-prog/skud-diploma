import sqlite3
import os
import datetime

DB_PATH = "skud.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            uid TEXT PRIMARY KEY,
            rank INTEGER NOT NULL,
            secret_key BLOB NOT NULL,
            current_zone INTEGER NOT NULL DEFAULT 0  -- Новое поле
        )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_history (
        uid TEXT,
        zone_id INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(uid) REFERENCES users(uid)
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
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица блокировок
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS access_blocks (
            uid TEXT PRIMARY KEY,
            fail_count INTEGER NOT NULL DEFAULT 0,
            blocked_until DATETIME
        )
    ''')
    
    # Таблица временных сессий
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pending_passes (
            uid TEXT PRIMARY KEY,
            zone_from INTEGER NOT NULL,
            zone_to INTEGER NOT NULL,
            authorized_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Базовые зоны
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

def get_user_current_zone(uid: str):
    """Получает текущую зону пользователя."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT current_zone FROM users WHERE uid = ?", (uid,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def update_user_current_zone(uid: str, zone_id: int):
    """Обновляет текущую зону пользователя."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET current_zone = ? WHERE uid = ?", (zone_id, uid))
    conn.commit()
    conn.close()
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

def check_block(uid: str):
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
            return True, fail_count
    
    return False, fail_count

def increment_fail(uid: str):
    conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM access_blocks WHERE uid = ?", (uid,))
    conn.commit()
    conn.close()

def create_pending_pass(uid: str, zone_from: int, zone_to: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO pending_passes (uid, zone_from, zone_to)
        VALUES (?, ?, ?)
    ''', (uid, zone_from, zone_to))
    conn.commit()
    conn.close()

def confirm_pass(uid: str):
    print(f"DEBUG: confirm_pass вызван для UID = {uid}")  # ← 1. Проверка вызова
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pending_passes WHERE uid = ?", (uid,))
    pass_data = cursor.fetchone()
    
    if pass_data:
        print(f"DEBUG: Найдена запись в pending_passes: {pass_data}")  # ← 2. Проверка данных
        
        uid, zone_from, zone_to, _ = pass_data
        
        # Обновление текущей зоны
        update_user_current_zone(uid, zone_to)
        
        # Запись в журнал
        log_access(uid, zone_from, zone_to, True, "Проход подтверждён")
        print(f"DEBUG: Запись в access_logs создана")  # ← 3. Проверка записи
        
        cursor.execute("DELETE FROM pending_passes WHERE uid = ?", (uid,))
        conn.commit()
    else:
        print(f"DEBUG: Запись в pending_passes НЕ найдена!")  # ← 4. Если данных нет
    
    conn.close()
    
def cleanup_expired_passes():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM pending_passes 
        WHERE datetime(authorized_at) < datetime('now', '-30 seconds')
    ''')
    conn.commit()
    conn.close()

def get_pending_pass(uid: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pending_passes WHERE uid = ?", (uid,))
    pass_data = cursor.fetchone()
    conn.close()
    return pass_data