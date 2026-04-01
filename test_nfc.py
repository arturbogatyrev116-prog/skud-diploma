"""
Тест NFC модуля для системы СКУД
Проверка чтения UID и записи NTAG
"""
import sys
import time
from nfc_reader import NFCReader

def test_nfc_basic():
    """Базовый тест чтения UID"""
    print("\n" + "="*60)
    print("ТЕСТ: Базовое чтение UID")
    print("="*60)
    
    reader = NFCReader()
    
    if not reader.init():
        print("❌ Ошибка инициализации PN532")
        return False
    
    print("✅ PN532 инициализирован")
    print("\nПриложите карту в течение 10 секунд...")
    
    uid = reader.read_card_uid(timeout=10000)
    
    if uid:
        print(f"\n✅ Карта обнаружена: {uid}")
        
        # Попытка прочитать данные NTAG
        print("\nЧтение данных NTAG (страницы 4-7)...")
        data = reader.read_ntag_data(page=4, count=4)
        if data:
            print(f"   Данные: {data.hex()}")
        else:
            print("   Нет данных или ошибка чтения")
        
        reader.close()
        return True
    else:
        print("\n❌ Карта не обнаружена")
        reader.close()
        return False


def test_nfc_write():
    """Тест записи данных на NTAG"""
    print("\n" + "="*60)
    print("ТЕСТ: Запись данных на NTAG")
    print("="*60)
    
    reader = NFCReader()
    
    if not reader.init():
        print("❌ Ошибка инициализации PN532")
        return False
    
    print("\nПриложите карту для записи (10 секунд)...")
    uid = reader.read_card_uid(timeout=10000)
    
    if not uid:
        print("❌ Карта не обнаружена")
        reader.close()
        return False
    
    print(f"✅ Карта: {uid}")
    
    # Данные для записи
    test_data = b"SKUD_TEST_1234"
    print(f"\nЗапись данных: {test_data}")
    
    # Запись на страницу 4
    success = reader.write_ntag_data(page=4, data=test_data)
    
    if success:
        print("✅ Запись успешна")
        
        # Чтение для проверки
        print("\nЧтение для проверки...")
        data = reader.read_ntag_data(page=4, count=4)
        if data:
            print(f"   Прочитано: {data.hex()}")
            if data.startswith(test_data):
                print("   ✅ Данные совпадают!")
            else:
                print("   ⚠️ Данные не совпадают")
    else:
        print("❌ Ошибка записи")
    
    reader.close()
    return True


def test_nfc_continuous():
    """Тест непрерывного чтения"""
    print("\n" + "="*60)
    print("ТЕСТ: Непрерывное чтение (Ctrl+C для выхода)")
    print("="*60)
    
    reader = NFCReader()
    
    if not reader.init():
        print("❌ Ошибка инициализации PN532")
        return False
    
    last_uid = None
    last_time = 0
    read_count = 0
    
    print("\nОжидание карт...")
    
    try:
        while True:
            uid = reader.read_card_uid(timeout=500)
            
            if uid:
                current_time = time.time()
                
                # Проверка cooldown (защита от повторных срабатываний)
                if uid != last_uid or (current_time - last_time) > 2:
                    read_count += 1
                    print(f"\n[{read_count}] Карта: {uid}")
                    last_uid = uid
                    last_time = current_time
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print(f"\n\nЗавершение. Всего прочтений: {read_count}")
    
    reader.close()
    return True


def test_nfc_emulation():
    """Тест в режиме эмуляции (без железа)"""
    print("\n" + "="*60)
    print("ТЕСТ: Режим эмуляции (без PN532)")
    print("="*60)
    
    reader = NFCReader()
    
    # Принудительная эмуляция
    import nfc_reader
    nfc_reader.PN532_AVAILABLE = False
    
    if reader.init():
        print("✅ Эмуляция инициализации успешна")
        print("   (режим без железа активен)")
        return True
    else:
        print("❌ Ошибка эмуляции")
        return False


def main():
    print("\n" + "█"*60)
    print("█ ТЕСТ NFC МОДУЛЯ СКУД")
    print("█"*60)
    
    tests = [
        ("Базовое чтение", test_nfc_basic),
        ("Запись NTAG", test_nfc_write),
        ("Непрерывное чтение", test_nfc_continuous),
        ("Эмуляция", test_nfc_emulation),
    ]
    
    print("\nВыберите тест:")
    for i, (name, _) in enumerate(tests, 1):
        print(f"  {i}. {name}")
    print("  0. Выход")
    
    try:
        choice = int(input("\nВаш выбор: "))
        
        if choice == 0:
            print("Выход")
            return
        
        if 1 <= choice <= len(tests):
            tests[choice-1][1]()
        else:
            print("Неверный выбор")
            
    except ValueError:
        print("Ошибка ввода")
    except Exception as e:
        print(f"Ошибка: {e}")


if __name__ == "__main__":
    main()
