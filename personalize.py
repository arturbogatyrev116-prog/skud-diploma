"""
Скрипт персонализации пользователей для системы СКУД
Добавляет новых пользователей в базу данных
"""
import os
import argparse
import logging
from database import init_db, add_user

# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    # Гарантируем, что таблицы существуют
    init_db()

    parser = argparse.ArgumentParser(
        description='Персонализация пользователя для СКУД',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Примеры использования:
  %(prog)s --uid ADMIN_01 --rank 9 --name "Администратор"
  %(prog)s --uid EMPLOYEE_123 --rank 5 --name "Иванов И.И."
  %(prog)s --uid VISITOR_001 --rank 3
        '''
    )
    parser.add_argument(
        '--uid',
        required=True,
        help='Уникальный ID пользователя (например, ID карты NFC)'
    )
    parser.add_argument(
        '--rank',
        type=int,
        required=True,
        choices=range(3, 10),
        metavar='3-9',
        help='Ранг пользователя (3=Посетитель, 9=Админ)'
    )
    parser.add_argument(
        '--name',
        default='User',
        help='Имя пользователя для отображения в логах'
    )
    args = parser.parse_args()

    # Генерация криптографически стойкого секретного ключа
    secret_key = os.urandom(32)

    # Сохранение в БД сервера
    add_user(args.uid, args.rank, secret_key)
    
    print("\n" + "="*50)
    print("✅ КАРТА ПЕРСОНАЛИЗИРОВАНА")
    print("="*50)
    print(f"  UID: {args.uid}")
    print(f"  Имя: {args.name}")
    print(f"  Ранг: {args.rank}")
    print(f"  Секретный ключ (hex): {secret_key.hex()[:32]}...")
    print("="*50)
    print("⚠️  Сохраните секретный ключ в безопасном месте!")
    print("    Он не будет отображаться повторно.\n")
    
    logger.info(f"Добавлен пользователь {args.uid} с рангом {args.rank}")


if __name__ == "__main__":
    main()
