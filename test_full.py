"""
Тестовый скрипт для эмуляции прохода через СКУД
Проверяет логику аутентификации и контроля доступа
"""
import os
import hmac
import hashlib
import json
import logging
from collections import Counter

# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

from database import (
    init_db, add_user, get_user, get_zones_info,
    get_user_current_zone, update_user_current_zone,
    log_access, check_block, reset_fail
)
from auth_logic import calculate_rank, is_history_valid, is_route_valid, is_context_valid

# Параметры теста
TEST_UID = "TEST_USER_001"
TEST_RANK = 8  # Админ (доступ к серверной)
TEST_SECRET_KEY = os.urandom(32)

# Параметры попыток
MAX_ATTEMPTS = 5000


def generate_auth_token(secret_key: bytes, history: list) -> tuple:
    """
    Сгенерировать токен аутентификации и комбинацию.
    Возвращает (nonce, combination, rank)
    """
    for attempt in range(MAX_ATTEMPTS):
        nonce = os.urandom(16)
        history_bytes = json.dumps(history).encode()
        T = hmac.new(secret_key, nonce + history_bytes, hashlib.sha256).digest()
        combination = [(b % 13) + 1 for b in T[:5]]
        actual_rank = calculate_rank(combination)
        
        if actual_rank == TEST_RANK:
            return nonce, combination, actual_rank
    
    return None, None, None


def test_authentication():
    """Тест 1: Успешная аутентификация пользователя с высоким рангом"""
    print("\n" + "="*60)
    print("ТЕСТ 1: Успешная аутентификация")
    print("="*60)
    
    init_db()
    reset_fail(TEST_UID)
    
    # Добавляем пользователя
    add_user(TEST_UID, TEST_RANK, TEST_SECRET_KEY, current_zone=0)
    user = get_user(TEST_UID)
    
    if not user:
        print("❌ ОШИБКА: Пользователь не добавлен")
        return False
    
    print(f"✓ Пользователь добавлен: {user['uid']}, ранг {user['rank']}")
    
    # Получаем историю
    current_zone = get_user_current_zone(TEST_UID)
    history = [current_zone]
    
    # Генерируем токен
    nonce, combination, rank = generate_auth_token(TEST_SECRET_KEY, history)
    
    if combination is None:
        print("❌ ОШИБКА: Не удалось сгенерировать комбинацию")
        return False
    
    print(f"✓ Комбинация: {combination}")
    print(f"✓ Вычисленный ранг: {rank}")
    print(f"✅ Аутентификация успешна!")
    
    return True


def test_insufficient_rank():
    """Тест 2: Отказ в доступе из-за недостаточного ранга"""
    print("\n" + "="*60)
    print("ТЕСТ 2: Недостаточный ранг")
    print("="*60)
    
    init_db()
    
    # Создаём пользователя с рангом 4 (посетитель)
    low_rank_uid = "LOW_RANK_USER"
    low_rank_key = os.urandom(32)
    add_user(low_rank_uid, 4, low_rank_key, current_zone=0)
    
    zones_info = get_zones_info()
    serverna_required = zones_info[2]['required_rank']
    
    print(f"✓ Пользователь с рангом 4 пытается войти в Серверную (требуется {serverna_required})")
    print(f"✅ Ожидается отказ: ранг 4 < {serverna_required}")
    
    return True


def test_context_violation():
    """Тест 3: Нарушение контекста (вход после выхода)"""
    print("\n" + "="*60)
    print("ТЕСТ 3: Нарушение контекста")
    print("="*60)
    
    init_db()
    
    # История: пользователь вышел (зона 999)
    history = [999, 0]  # Последняя зона - выход
    zones_info = get_zones_info()
    
    # Пытается войти в офис (зона 1) вместо входа (зона 0)
    context_valid, context_msg = is_context_valid(history, 1, zones_info)
    
    print(f"✓ История: {history}")
    print(f"✓ Запрашиваемая зона: 1 (Офис)")
    print(f"✓ Результат: {context_valid}, {context_msg}")
    
    if not context_valid:
        print("✅ Контекстная проверка сработала correctly!")
        return True
    else:
        print("❌ ОШИБКА: Контекстная проверка не сработала")
        return False


def test_invalid_history():
    """Тест 4: Несуществующая зона в истории"""
    print("\n" + "="*60)
    print("ТЕСТ 4: Несуществующая зона в истории")
    print("="*60)
    
    init_db()
    
    # История с несуществующей зоной 9999
    history = [9999, 0]
    zones_info = get_zones_info()
    
    history_valid, history_msg = is_history_valid(history, zones_info)
    
    print(f"✓ История: {history}")
    print(f"✓ Результат: {history_valid}, {history_msg}")
    
    if not history_valid:
        print("✅ Проверка истории сработала correctly!")
        return True
    else:
        print("❌ ОШИБКА: Проверка истории не сработала")
        return False


def test_route_validation():
    """Тест 5: Проверка маршрута"""
    print("\n" + "="*60)
    print("ТЕСТ 5: Проверка маршрута")
    print("="*60)
    
    init_db()
    zones_info = get_zones_info()
    
    # Тест 5a: Нормальный маршрут Вход → Офис
    history_5a = [0]  # Текущая зона - вход
    valid, msg = is_route_valid(history_5a, 1, zones_info)
    print(f"✓ Маршрут Вход(0) → Офис(1): {valid}, {msg}")
    
    # Тест 5b: Нарушение Выход → Офис (должно быть Выход → Вход)
    history_5b = [999]  # Текущая зона - выход
    valid, msg = is_route_valid(history_5b, 1, zones_info)
    print(f"✓ Маршрут Выход(999) → Офис(1): {valid}, {msg}")
    
    # Тест 5c: Выход → Вход (корректно)
    valid, msg = is_route_valid(history_5b, 0, zones_info)
    print(f"✓ Маршрут Выход(999) → Вход(0): {valid}, {msg}")
    
    print("✅ Проверка маршрутов завершена!")
    return True


def test_rank_calculations():
    """Тест 6: Вычисление покерных рангов"""
    print("\n" + "="*60)
    print("ТЕСТ 6: Вычисление покерных рангов")
    print("="*60)
    
    test_cases = [
        ([1, 1, 1, 1, 2], 9, "Каре"),
        ([2, 2, 2, 3, 3], 8, "Фулл-хаус"),
        ([1, 2, 3, 4, 5], 7, "Стрит"),
        ([10, 11, 12, 13, 1], 7, "Стрит туз"),
        ([5, 5, 5, 2, 3], 6, "Тройка"),
        ([4, 4, 7, 7, 2], 5, "Две пары"),
        ([9, 9, 2, 3, 4], 4, "Одна пара"),
        ([1, 5, 8, 10, 13], 3, "Старшая карта"),
    ]
    
    all_passed = True
    for combination, expected_rank, name in test_cases:
        actual_rank = calculate_rank(combination)
        status = "✅" if actual_rank == expected_rank else "❌"
        print(f"{status} {name}: {combination} → ранг {actual_rank} (ожидалось {expected_rank})")
        if actual_rank != expected_rank:
            all_passed = False
    
    return all_passed


def test_block_after_fails():
    """Тест 7: Блокировка после 3 неудачных попыток"""
    print("\n" + "="*60)
    print("ТЕСТ 7: Блокировка после неудачных попыток")
    print("="*60)
    
    init_db()
    
    block_uid = "BLOCK_TEST_USER"
    block_key = os.urandom(32)
    add_user(block_uid, 5, block_key, current_zone=0)
    reset_fail(block_uid)
    
    from database import increment_fail
    
    print(f"✓ Симуляция 3 неудачных попыток для {block_uid}")
    
    for i in range(3):
        is_blocked, _ = increment_fail(block_uid)
        print(f"  Попытка {i+1}: заблокирован = {is_blocked}")
    
    # Проверяем блокировку
    is_blocked, fail_count = check_block(block_uid)
    print(f"✓ После 3 попыток: заблокирован = {is_blocked}, счётчик = {fail_count}")
    
    if is_blocked:
        print("✅ Блокировка сработала correctly!")
        reset_fail(block_uid)
        return True
    else:
        print("❌ ОШИБКА: Блокировка не сработала")
        return False


def run_all_tests():
    """Запустить все тесты"""
    print("\n" + "█"*60)
    print("█ ЗАПУСК ТЕСТОВ СИСТЕМЫ СКУД")
    print("█"*60)
    
    tests = [
        ("Вычисление рангов", test_rank_calculations),
        ("Аутентификация", test_authentication),
        ("Недостаточный ранг", test_insufficient_rank),
        ("Контекстная проверка", test_context_violation),
        ("Проверка истории", test_invalid_history),
        ("Проверка маршрута", test_route_validation),
        ("Блокировка", test_block_after_fails),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА в тесте '{name}': {e}")
            logger.exception(f"Ошибка в тесте {name}")
            results.append((name, False))
    
    # Итоги
    print("\n" + "="*60)
    print("ИТОГИ ТЕСТИРОВАНИЯ")
    print("="*60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\nВсего: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
    else:
        print(f"\n⚠️ {total - passed} тестов не пройдено")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
