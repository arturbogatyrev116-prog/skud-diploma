"""
Конфигурация системы СКУД
"""
import os
from dotenv import load_dotenv

load_dotenv()

# База данных
DB_PATH = "skud.db"

# Секретный ключ Flask — задаётся через переменную окружения SKUD_SECRET_KEY в .env
_secret = os.environ.get("SKUD_SECRET_KEY")
if not _secret:
    raise RuntimeError("SKUD_SECRET_KEY не задан. Скопируйте .env.example в .env и задайте ключ.")
SECRET_KEY = _secret

# Ключ шифрования NFC-токенов (Fernet). Если не задан — токены не генерируются.
NFC_TOKEN_KEY = os.environ.get("NFC_TOKEN_KEY", "")

# Параметры аутентификации
MAX_ATTEMPTS_RANK_HIGH = 5000    # Для ранга 8-9
MAX_ATTEMPTS_RANK_MEDIUM = 1000  # Для ранга 7
MAX_ATTEMPTS_RANK_LOW = 100       # Для ранга 3-6

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

# NFC настройки
NFC_INTERFACE = os.environ.get("NFC_INTERFACE", "spi")  # 'spi', 'i2c', 'uart'
NFC_RST_PIN = int(os.environ.get("NFC_RST_PIN", "17"))
NFC_IRQ_PIN = int(os.environ.get("NFC_IRQ_PIN", "24"))
NFC_SPI_CE = int(os.environ.get("NFC_SPI_CE", "0"))
NFC_UART_PORT = os.environ.get("NFC_UART_PORT", "/dev/serial0")
