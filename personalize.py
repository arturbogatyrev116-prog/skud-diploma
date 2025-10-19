# personalize.py
import os
import argparse
from database import init_db, add_user

def main():
    init_db()  # ← ГАРАНТИРУЕМ, что таблицы существуют
    parser = argparse.ArgumentParser(description='Персонализация NFC-карты для СКУД')
    parser.add_argument('--uid', required=True, help='Уникальный ID карты (например, A1B2C3D4)')
    parser.add_argument('--rank', type=int, required=True, choices=range(3,10), 
                        help='Ранг пользователя (3-9)')
    parser.add_argument('--name', default='User', help='Имя пользователя (для логов)')
    
    args = parser.parse_args()
    
    # Генерация секретного ключа (в реальной жизни — запись в защищённую память карты)
    secret_key = os.urandom(32)
    
    # Сохранение в БД сервера
    add_user(args.uid, args.rank, secret_key)
    
    print(f"✅ Карта персонализирована!")
    print(f"  UID: {args.uid}")
    print(f"  Имя: {args.name}")
    print(f"  Ранг: {args.rank}")
    print(f"  Секретный ключ (hex): {secret_key.hex()[:32]}...")

if __name__ == "__main__":
    main()