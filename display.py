# display.py
import pygame
import sqlite3
import time
from datetime import datetime

# Инициализация Pygame
pygame.init()
screen = pygame.display.set_mode((800, 480))
pygame.display.set_caption("СКУД: Схема помещения")

# Цвета
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

# Шрифт
font = pygame.font.SysFont('Arial', 20)

# Схема помещения (координаты точек входа)
zones = {
    "Главный вход": (100, 150),
    "Серверная": (400, 200),
    "Выход": (700, 150)
}

# Функция чтения последнего события
def get_last_event():
    conn = sqlite3.connect("skud.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM access_logs ORDER BY timestamp DESC LIMIT 1")
    event = cursor.fetchone()
    conn.close()
    return event

# Основной цикл
running = True
last_update = 0

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    
    # Очистка экрана
    screen.fill(WHITE)
    
    # Рисуем схему
    pygame.draw.rect(screen, BLACK, (50, 50, 700, 300), 2)
    for name, pos in zones.items():
        color = BLUE
        # Если последнее событие — эта зона, мигаем красным
        last_event = get_last_event()
        if last_event and last_event[3] == pos[0]:  # zone_from
            color = RED
        pygame.draw.circle(screen, color, pos, 10)
        text = font.render(name, True, BLACK)
        screen.blit(text, (pos[0] + 15, pos[1] - 10))
    
    # Вывод информации о последнем событии
    last_event = get_last_event()
    if last_event:
        uid = last_event[1]
        zone_from = last_event[2]
        zone_to = last_event[3]
        success = last_event[4]
        reason = last_event[5]
        timestamp = last_event[6]
        
        status = "✅" if success else "❌"
        info_text = f"{status} {zone_from}→{zone_to} | UID:{uid} | {timestamp}"
        info_surface = font.render(info_text, True, BLACK)
        screen.blit(info_surface, (50, 380))
    
    # Обновление экрана
    pygame.display.flip()
    time.sleep(1)  # Обновляем каждую секунду

pygame.quit()