from collections import Counter

def is_history_valid(history, zones_info):
    for zone_id in history:
        if zone_id not in zones_info:
            return False, f"История содержит несуществующую зону: {zone_id}"
    return True, "OK" 

def calculate_rank(combination):
    """Вычисляет ранг покерной комбинации (3–9)."""
    if len(combination) != 5:
        raise ValueError("Комбинация должна содержать 5 карт")
    sorted_comb = sorted(combination)
    counts = Counter(combination)
    freqs = sorted(counts.values(), reverse=True)

    if freqs == [4, 1]:
        return 9  # Каре
    if freqs == [3, 2]:
        return 8  # Фулл-хаус
    is_straight = sorted_comb == list(range(sorted_comb[0], sorted_comb[0] + 5))
    is_ace_straight = sorted_comb == [1, 10, 11, 12, 13]
    if is_straight or is_ace_straight:
        return 7  # Стрит
    if freqs == [3, 1, 1]:
        return 6  # Тройка
    if freqs == [2, 2, 1]:
        return 5  # Две пары
    if freqs == [2, 1, 1, 1]:
        return 4  # Пара
    return 3  # Старшая карта

def is_context_valid(history, requested_zone, zones_info):
    """
    Проверяет корректность маршрута.
    history: [последняя_зона, предпоследняя_зона]
    requested_zone: зона, куда хочет попасть пользователь
    zones_info: словарь {id_зоны: {'is_exit': bool}}
    """
    last_zone = history[0]
    
    # Правило 1: Из зоны "выход" (999) нельзя попасть никуда, кроме "входа" (0)
    if last_zone == 999:
        if requested_zone != 0:
            return False, "Запрещён вход после выхода"
    
    # Правило 2: Нельзя "выйти" из обычной зоны напрямую на улицу (если нет зоны 'Выход')
    # (можно расширить по вашему сценарию)
    
    return True, "OK"