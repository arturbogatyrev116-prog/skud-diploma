# auth_logic.py
from collections import Counter

def calculate_rank(combination):
    if len(combination) != 5:
        raise ValueError("Комбинация должна содержать 5 карт")
    sorted_comb = sorted(combination)
    counts = Counter(combination)
    freqs = sorted(counts.values(), reverse=True)

    if freqs == [4, 1]:
        return 9
    if freqs == [3, 2]:
        return 8
    is_straight = sorted_comb == list(range(sorted_comb[0], sorted_comb[0] + 5))
    is_ace_straight = sorted_comb == [1, 10, 11, 12, 13]
    if is_straight or is_ace_straight:
        return 7
    if freqs == [3, 1, 1]:
        return 6
    if freqs == [2, 2, 1]:
        return 5
    if freqs == [2, 1, 1, 1]:
        return 4
    return 3

def is_context_valid(history, requested_zone, zones_info):
    last_zone = history[0]
    if last_zone == 999:
        if requested_zone != 0:
            return False, "Запрещён вход после выхода"
    return True, "OK"

def is_history_valid(history, zones_info):
    for zone_id in history:
        if zone_id not in zones_info:
            return False, f"История содержит несуществующую зону: {zone_id}"
    return True, "OK"