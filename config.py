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

# Зоны по умолчанию
DEFAULT_ZONES = [
    (0, 'Вход', False, 3),
    (1, 'Офис', False, 5),
    (2, 'Серверная', False, 8),
    (999, 'Выход', True, 3)
]

# Логирование
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
LOG_LEVEL = "INFO"
