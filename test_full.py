# test_full.py
import os
import hmac
import hashlib
from database import init_db, add_user, get_user, log_access, get_zones_info, check_block, increment_fail, reset_fail
import datetime
from auth_logic import calculate_rank, is_history_valid
import sqlite3
init_db()

# === Настройка пользователя ===
USER_UID = "ADMIN_01"
SECRET_KEY = os.urandom(32)
USER_RANK = 9  
add_user(USER_UID, USER_RANK, SECRET_KEY)

HISTORY = [-1, 9999]          
REQUESTED_ZONE = 0      

print(f"Пользователь: {USER_UID} (ранг {USER_RANK})")
print(f"История: {HISTORY} → запрашивает зону {REQUESTED_ZONE}")

user = get_user(USER_UID)
if not user:
    print("❌ Пользователь не найден")
    exit()

zones_info = get_zones_info()
if REQUESTED_ZONE not in zones_info:
    print(f"❌ Зона {REQUESTED_ZONE} не существует")
    exit()

history_valid, history_msg = is_history_valid(HISTORY, zones_info)
if not history_valid:
    log_access(USER_UID, HISTORY[0], REQUESTED_ZONE, False, f"Некорректная история: {history_msg}")
    print(f"❌ {history_msg}")
    exit()

# === Проверка блокировки ===
is_blocked, fail_count = check_block(USER_UID)
if is_blocked:
    # Рассчитываем оставшееся время
    conn = sqlite3.connect("skud.db")
    cursor = conn.cursor()
    cursor.execute("SELECT blocked_until FROM access_blocks WHERE uid = ?", (USER_UID,))
    blocked_until = datetime.datetime.fromisoformat(cursor.fetchone()[0])
    conn.close()
    remaining = (blocked_until - datetime.datetime.now()).total_seconds()
    if remaining > 0:
        print(f"❌ Доступ заблокирован на {int(remaining)} секунд из-за 3 неудачных попыток")
        exit()

required_rank = zones_info[REQUESTED_ZONE]['required_rank']
print(f"Требуемый ранг для зоны '{REQUESTED_ZONE}': {required_rank}")

# === АВТОМАТИЧЕСКИЕ ПОПЫТКИ ===
MAX_ATTEMPTS = 5000
print(f"Поиск комбинации с рангом {USER_RANK} (макс. {MAX_ATTEMPTS} попыток)...")

for attempt in range(1, MAX_ATTEMPTS + 1):
    nonce = os.urandom(16)
    history_bytes = str(HISTORY).encode()
    T = hmac.new(user['secret_key'], nonce + history_bytes, hashlib.sha256).digest()
    combination = [(b % 13) + 1 for b in T[:5]]
    actual_rank = calculate_rank(combination)
    
    if actual_rank == USER_RANK:
        print(f"✅ Успех на попытке #{attempt}!")
        print(f"Сгенерированная комбинация: {combination} → ранг {actual_rank}")
        
        # === ШАГ 2: Авторизация (права доступа) ===
        if user['rank'] >= required_rank:
            reason = f"Успех: ранг {user['rank']} >= {required_rank}"
            log_access(USER_UID, HISTORY[0], REQUESTED_ZONE, True, reason)
            print(f"✅ ДОСТУП РАЗРЕШЁН!")
        else:
            reason = f"Недостаточно прав: ранг {user['rank']} < {required_rank}"
            log_access(USER_UID, HISTORY[0], REQUESTED_ZONE, False, reason)
            print(f"❌ {reason}")
        exit()
auth_success = False
# Если цикл завершился без успеха
reason = f"Не удалось сгенерировать ранг {USER_RANK} за {MAX_ATTEMPTS} попыток"
log_access(USER_UID, HISTORY[0], REQUESTED_ZONE, False, reason)
print(f"❌ {reason}")
if user['rank'] >= required_rank:
    reset_fail(USER_UID)  # Сбросить счётчик
    # ... логирование и вывод
if not auth_success:
    is_blocked, blocked_time = increment_fail(USER_UID)
    if is_blocked:
        print(f"❌ Доступ заблокирован на 1 минуту из-за 3 неудачных попыток")
    else:
        print(f"❌ Неудачная попытка ({fail_count + 1}/3)")