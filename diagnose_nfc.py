#!/usr/bin/env python3
"""
Диагностика подключения PN532 к Raspberry Pi 4B.
Запускать на самом Raspberry Pi:
  python3 diagnose_nfc.py
  python3 diagnose_nfc.py --interface i2c
  python3 diagnose_nfc.py --interface uart
"""
import sys
import time
import argparse
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def check_spi():
    print("\n--- Проверка SPI ---")
    import os
    devs = [d for d in ['/dev/spidev0.0', '/dev/spidev0.1'] if os.path.exists(d)]
    if devs:
        print(f"  ✅ SPI устройства: {devs}")
    else:
        print("  ❌ SPI устройства не найдены.")
        print("     Включите SPI: sudo raspi-config → Interface Options → SPI")
        return False

    try:
        import spidev
        spi = spidev.SpiDev()
        spi.open(0, 0)
        spi.max_speed_hz = 500000
        resp = spi.xfer2([0x00])
        spi.close()
        print(f"  ✅ SPI шина работает (ответ: {resp})")
        return True
    except Exception as e:
        print(f"  ❌ Ошибка SPI: {e}")
        return False


def check_i2c():
    print("\n--- Проверка I2C ---")
    import os
    if not os.path.exists('/dev/i2c-1'):
        print("  ❌ I2C не включён.")
        print("     Включите I2C: sudo raspi-config → Interface Options → I2C")
        return False
    print("  ✅ /dev/i2c-1 доступен")

    try:
        import smbus2
        bus = smbus2.SMBus(1)
        found = []
        for addr in range(0x03, 0x78):
            try:
                bus.read_byte(addr)
                found.append(hex(addr))
            except Exception:
                pass
        bus.close()
        if found:
            print(f"  ✅ I2C устройства найдены: {found}")
            if '0x24' in found:
                print("  ✅ PN532 обнаружен по адресу 0x24")
        else:
            print("  ⚠️  I2C устройства не найдены. Проверьте подключение и переключатели SET0=H, SET1=L")
        return True
    except ImportError:
        print("  ⚠️  smbus2 не установлен. Установите: pip3 install smbus2")
        # Пробуем через i2cdetect
        ret = os.system("i2cdetect -y 1 2>/dev/null")
        return ret == 0
    except Exception as e:
        print(f"  ❌ Ошибка I2C: {e}")
        return False


def check_uart():
    print("\n--- Проверка UART ---")
    import os
    ports = ['/dev/serial0', '/dev/ttyS0', '/dev/ttyAMA0']
    found = [p for p in ports if os.path.exists(p)]
    if found:
        print(f"  ✅ UART порты: {found}")
    else:
        print("  ❌ UART порты не найдены.")
        print("     Включите Serial: sudo raspi-config → Interface Options → Serial Port")
        return False
    return True


def check_gpio():
    print("\n--- Проверка GPIO ---")
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(17, GPIO.OUT)
        GPIO.output(17, GPIO.HIGH)
        time.sleep(0.1)
        GPIO.output(17, GPIO.LOW)
        time.sleep(0.1)
        GPIO.output(17, GPIO.HIGH)
        GPIO.cleanup()
        print("  ✅ GPIO 17 (RST) работает")
        return True
    except ImportError:
        print("  ⚠️  RPi.GPIO не установлен (нормально на не-RPi системах)")
        return True
    except Exception as e:
        print(f"  ❌ Ошибка GPIO: {e}")
        return False


def check_adafruit():
    print("\n--- Проверка библиотеки Adafruit ---")
    try:
        import adafruit_pn532
        print("  ✅ adafruit-circuitpython-pn532 установлена")
    except ImportError:
        print("  ❌ Библиотека не найдена.")
        print("     Установите: pip3 install adafruit-circuitpython-pn532 --break-system-packages")
        return False

    try:
        import board
        import busio
        import digitalio
        print("  ✅ board, busio, digitalio доступны")
        return True
    except ImportError as e:
        print(f"  ❌ Ошибка импорта CircuitPython: {e}")
        print("     Установите: pip3 install adafruit-blinka --break-system-packages")
        return False


def test_pn532(interface: str):
    print(f"\n--- Тест PN532 через {interface.upper()} ---")
    try:
        from nfc_reader import NFCReader
        reader = NFCReader(interface=interface)
        if reader.init():
            print(f"  ✅ PN532 инициализирован через {interface.upper()}")
            print("  Приложите карту (5 секунд)...")
            uid = reader.wait_for_card(timeout=5)
            if uid:
                print(f"  ✅ Карта обнаружена: {uid}")
            else:
                print("  ⚠️  Карта не приложена за 5 секунд")
            reader.close()
            return True
        else:
            print(f"  ❌ Не удалось инициализировать PN532 через {interface.upper()}")
            return False
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Диагностика PN532 на Raspberry Pi 4B')
    parser.add_argument('--interface', '-i', default='spi',
                        choices=['spi', 'i2c', 'uart'],
                        help='Интерфейс подключения (по умолчанию: spi)')
    parser.add_argument('--skip-pn532', action='store_true',
                        help='Пропустить тест PN532 (только проверка системы)')
    args = parser.parse_args()

    print("=" * 50)
    print("ДИАГНОСТИКА PN532 — Raspberry Pi 4B")
    print("=" * 50)

    results = {}

    # Проверка библиотеки
    results['adafruit'] = check_adafruit()

    # Проверка интерфейса
    if args.interface == 'spi':
        results['interface'] = check_spi()
    elif args.interface == 'i2c':
        results['interface'] = check_i2c()
    elif args.interface == 'uart':
        results['interface'] = check_uart()

    # Проверка GPIO
    results['gpio'] = check_gpio()

    # Тест PN532
    if not args.skip_pn532 and results.get('adafruit') and results.get('interface'):
        results['pn532'] = test_pn532(args.interface)

    # Итог
    print("\n" + "=" * 50)
    print("ИТОГ")
    print("=" * 50)
    for name, ok in results.items():
        status = "✅" if ok else "❌"
        print(f"  {status} {name}")

    if all(results.values()):
        print("\n✅ Всё в порядке! PN532 готов к работе.")
        print(f"   Установите в .env: NFC_INTERFACE={args.interface}")
    else:
        print("\n⚠️  Есть проблемы. Следуйте рекомендациям выше.")

    print("\nПодсказки по питанию:")
    print("  • Используй пин 5V (Pin 2 или 4) для питания модуля, не 3.3V")
    print("  • Встроенный стабилизатор модуля сам понизит 5V до 3.3V")
    print("  • Используй короткие провода (до 20 см)")
    print("  • Блок питания: минимум 5V/3A через USB-C")


if __name__ == "__main__":
    main()
