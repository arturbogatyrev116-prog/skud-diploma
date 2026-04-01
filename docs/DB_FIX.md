# 🔧 Исправление ошибки "no such column: created_at"

## Причина

База данных `skud.db` была создана старой версией `database.py` без колонки `created_at`.

---

## ✅ Решение 1: Миграция БД (сохраняет данные)

```bash
cd /home/artur/Desktop/skud/skud-diploma

# Запуск миграции
python3 migrate_db.py

# Проверка
python3 app.py
```

---

## ✅ Решение 2: Пересоздать БД (быстрее)

```bash
cd /home/artur/Desktop/skud/skud-diploma

# Удалить старую базу
rm skud.db

# Запустить app.py (создаст новую)
python3 app.py

# Добавить пользователей
python3 personalize.py --uid ADMIN_01 --rank 9 --name "Администратор"
```

---

## 🔍 Проверка структуры БД

```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('skud.db')
cursor = conn.cursor()
cursor.execute('PRAGMA table_info(users)')
print('Таблица users:')
for row in cursor.fetchall():
    print(f'  {row[1]}: {row[2]}')
conn.close()
"
```

**Ожидаемый результат:**
```
Таблица users:
  uid: TEXT
  rank: INTEGER
  secret_key: TEXT
  current_zone: INTEGER
  created_at: DATETIME
```

---

## 📝 На будущее

Чтобы избежать проблем с БД:

1. При изменении `database.py` запускайте миграции
2. Используйте `migrate_db.py` для обновления схемы
3. Храните миграции в папке `migrations/`
