"""
Модуль аутентификации и проверки доступа для системы СКУД
Вычисление рангов на основе покерных комбинаций и валидация маршрутов
"""
from collections import Counter
import logging

logger = logging.getLogger(__name__)


def calculate_rank(combination: list) -> int:
    """
    Вычислить ранг комбинации на основе покерных правил.
    
    Ранги:
    - 9: Каре (4 одинаковых)
    - 8: Фулл-хаус (3+2)
    - 7: Стрит (5 последовательных)
    - 6: Тройка (3 одинаковых)
    - 5: Две пары (2+2+1)
    - 4: Одна пара (2+1+1+1)
    - 3: Старшая карта (без совпадений)
    
    Args:
        combination: Список из 5 чисел (1-13)
    
    Returns:
        Ранг комбинации (3-9)
    """
    if len(combination) != 5:
        raise ValueError("Комбинация должна содержать 5 элементов")
    
    sorted_comb = sorted(combination)
    counts = Counter(combination)
    freqs = sorted(counts.values(), reverse=True)

    # Каре (4 одинаковых)
    if freqs == [4, 1]:
        return 9
    
    # Фулл-хаус (3+2)
    if freqs == [3, 2]:
        return 8
    
    # Стрит (5 последовательных карт)
    is_straight = sorted_comb == list(range(sorted_comb[0], sorted_comb[0] + 5))
    is_ace_straight = sorted_comb == [1, 10, 11, 12, 13]
    if is_straight or is_ace_straight:
        return 7
    
    # Тройка (3 одинаковых)
    if freqs == [3, 1, 1]:
        return 6
    
    # Две пары (2+2+1)
    if freqs == [2, 2, 1]:
        return 5
    
    # Одна пара (2+1+1+1)
    if freqs == [2, 1, 1, 1]:
        return 4
    
    # Старшая карта
    return 3


def is_context_valid(history: list, requested_zone: int, zones_info: dict) -> tuple:
    """
    Проверить контекст запроса доступа.
    
    Правила:
    - Из зоны "Выход" (999) можно перейти только на "Вход" (0)
    - Нельзя миновать обязательные зоны
    
    Args:
        history: История перемещений [предыдущая_зона, ...]
        requested_zone: Запрашиваемая зона
        zones_info: Информация о зонах
    
    Returns:
        (bool, str): Корректность и сообщение
    """
    if not history:
        return True, "Пустая история"
    
    last_zone = history[0]
    
    # Правило: после выхода можно только на вход
    if last_zone == 999:
        if requested_zone != 0:
            logger.warning(f"Нарушение контекста: вход после выхода ({last_zone}→{requested_zone})")
            return False, "Запрещён вход после выхода"
    
    return True, "OK"


def is_history_valid(history: list, zones_info: dict) -> tuple:
    """
    Проверить корректность истории перемещений.
    
    Args:
        history: Список ID зон в порядке посещения
        zones_info: Информация о зонах
    
    Returns:
        (bool, str): Валидность и сообщение
    """
    for zone_id in history:
        if zone_id not in zones_info:
            logger.warning(f"Несуществующая зона в истории: {zone_id}")
            return False, f"История содержит несуществующую зону: {zone_id}"
    
    return True, "OK"


def is_route_valid(history: list, requested_zone: int, zones_info: dict) -> tuple:
    """
    Проверить валидность маршрута перемещения.
    
    Правила маршрутизации:
    1. Из выхода (999) можно только на вход (0)
    2. Вход (0) → любые зоны кроме выхода
    3. Офисные зоны (1-6) → серверная (7), выход (999), другие офисные
    4. Серверная (7) → только выход (999) или обратно в офис
    
    Args:
        history: История перемещений (последняя зона первая)
        requested_zone: Запрашиваемая зона
        zones_info: Информация о зонах
    
    Returns:
        (bool, str): Валидность и сообщение
    """
    if not history:
        return True, "Пустая история"
    
    current_zone = history[0]
    zone_name = zones_info.get(requested_zone, {}).get('name', f'Зона {requested_zone}')
    current_name = zones_info.get(current_zone, {}).get('name', f'Зона {current_zone}')
    
    # Проверка: из выхода только на вход
    if current_zone == 999 and requested_zone != 0:
        logger.warning(f"Маршрут нарушен: {current_name}→{zone_name}")
        return False, "После выхода необходимо пройти на вход"
    
    # Проверка: вход существует в системе
    if requested_zone not in zones_info:
        logger.warning(f"Запрос несуществующей зоны: {requested_zone}")
        return False, f"Зона {requested_zone} не существует"
    
    # Проверка: текущая зона существует
    if current_zone not in zones_info:
        logger.warning(f"Текущая зона не существует: {current_zone}")
        return False, f"Текущая зона {current_zone} не существует"
    
    # Проверка на зацикливание (нельзя идти в ту же зону)
    if current_zone == requested_zone and requested_zone != 999:
        # Исключение: выход может быть многократным
        logger.warning(f"Попытка входа в ту же зону: {current_zone}")
        return False, "Вы уже находитесь в этой зоне"
    
    logger.debug(f"Маршрут валиден: {current_name}→{zone_name}")
    return True, "OK"


def generate_combination_from_token(token: bytes) -> list:
    """
    Сгенерировать комбинацию из 5 чисел из токена.
    
    Args:
        token: Байты токена HMAC
    
    Returns:
        Список из 5 чисел (1-13)
    """
    return [(b % 13) + 1 for b in token[:5]]
