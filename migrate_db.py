#!/usr/bin/env python3
"""
Скрипт миграции базы данных
Добавляет недостающие колонки в существующую БД
"""
import sqlite3
import sys

def migrate_db():
    conn = sqlite3.connect('skud.db')
    cursor = conn.cursor()
    
    print("🔧 Миграция базы данных...")
    
    # Проверяем таблицу users
    cursor.execute("PRAGMA table_info(users)")
    columns = {row[1] for row in cursor.fetchall()}
    
    print(f"  Найдено колонок в users: {len(columns)}")
    
    # Добавляем created_at если нет
    if 'created_at' not in columns:
        print("  ➕ Добавляем created_at...")
        cursor.execute("""
            ALTER TABLE users 
            ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        """)
        print("  ✅ created_at добавлена")
    else:
        print("  ℹ️  created_at уже существует")
    
    # Проверяем таблицу access_logs
    cursor.execute("PRAGMA table_info(access_logs)")
    log_columns = {row[1] for row in cursor.fetchall()}
    
    if 'timestamp' not in log_columns:
        print("  ➕ Добавляем timestamp в access_logs...")
        cursor.execute("""
            ALTER TABLE access_logs 
            ADD COLUMN timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        """)
        print("  ✅ timestamp добавлена")
    else:
        print("  ℹ️  timestamp уже существует")
    
    # Проверяем таблицу user_history
    cursor.execute("PRAGMA table_info(user_history)")
    history_columns = {row[1] for row in cursor.fetchall()}
    
    if 'timestamp' not in history_columns:
        print("  ➕ Добавляем timestamp в user_history...")
        cursor.execute("""
            ALTER TABLE user_history 
            ADD COLUMN timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        """)
        print("  ✅ timestamp добавлена")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Миграция завершена!")
    print("\nТеперь можно запустить:")
    print("  python3 app.py")

if __name__ == "__main__":
    try:
        migrate_db()
    except sqlite3.Error as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)
