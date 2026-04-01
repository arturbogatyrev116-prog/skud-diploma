#!/usr/bin/env python3
"""
Скрипт обновления зон в базе данных
Добавляет все 8 зон + Вход/Выход
"""
import sqlite3

def update_zones():
    conn = sqlite3.connect('skud.db')
    cursor = conn.cursor()
    
    print("🔄 Обновление зон в базе данных...")
    
    # Новые зоны (8 зон + Вход/Выход)
    zones = [
        (0, 'Вход', 0, 3),
        (1, 'Офис 1', 0, 5),
        (2, 'Офис 2', 0, 5),
        (3, 'Офис 3', 0, 5),
        (4, 'Кафетерий', 0, 4),
        (5, 'Склад', 0, 6),
        (6, 'Директор', 0, 7),
        (7, 'Серверная', 0, 8),
        (999, 'Выход', 1, 3)
    ]
    
    # Обновляем или добавляем зоны
    for zone_id, name, is_exit, required_rank in zones:
        cursor.execute("""
            INSERT OR REPLACE INTO zones (id, name, is_exit, required_rank)
            VALUES (?, ?, ?, ?)
        """, (zone_id, name, is_exit, required_rank))
    
    conn.commit()
    
    # Проверяем результат
    cursor.execute("SELECT * FROM zones ORDER BY id")
    print("\n✅ Зоны в базе данных:")
    for row in cursor.fetchall():
        print(f"  Зона {row[0]}: {row[1]} (требуется ранг {row[3]})")
    
    conn.close()
    
    print("\n✅ Обновление завершено!")
    print("\nТеперь перезапустите app.py:")
    print("  python3 app.py")

if __name__ == "__main__":
    try:
        update_zones()
    except sqlite3.Error as e:
        print(f"❌ Ошибка: {e}")
        import sys
        sys.exit(1)
