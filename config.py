"""
Конфигурация системы СКУД
"""
import os

# База данных
DB_PATH = "skud.db"

# Секретный ключ Flask (должен быть постоянным для сохранения сессий)
SECRET_KEY = os.environ.get("SKUD_SECRET_KEY", os.urandom(32))

# Параметры аутентификации
MAX_ATTEMPTS_RANK_HIGH = 5000    # Для ранга 8-9
MAX_ATTEMPTS_RANK_MEDIUM = 1000  # Для ранга 7
MAX_ATTEMPTS_RANK_LOW = 100      # Для ранга 3-6

# Блокировки
MAX_FAIL_COUNT = 3
BLOCK_DURATION_MINUTES = 1

# Временные сессии прохода
PASS_VALID_SECONDS = 10

# Ранги пользователей
MIN_RANK = 3
MAX_RANK = 9

# Зоны по умолчанию (8 зон + Вход/Выход)
# (id, название, is_exit, требуемый ранг)
DEFAULT_ZONES = [
    (0, 'Вход', False, 3),       # Вход/выход из здания
    (1, 'Офис 1', False, 5),     # Открытое пространство
    (2, 'Офис 2', False, 5),     # Открытое пространство
    (3, 'Офис 3', False, 5),     # Открытое пространство
    (4, 'Кафетерий', False, 4),  # Зона отдыха
    (5, 'Склад', False, 6),      # Материальные ценности
    (6, 'Директор', False, 7),   # Руководство
    (7, 'Серверная', False, 8),  # Критическая зона
    (999, 'Выход', True, 3)      # Выход из здания
]

# Логирование
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
LOG_LEVEL = "INFO"
