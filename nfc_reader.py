"""
Модуль работы с NFC-считывателем PN532 для Raspberry Pi 4B
Поддерживает SPI, I2C и UART интерфейсы.

Выбор интерфейса через переключатели на плате:
  UART: SET0=L, SET1=L
  SPI:  SET0=L, SET1=H  (рекомендуется)
  I2C:  SET0=H, SET1=L

Подключение SPI (рекомендуется):
  SCK  → Pin 23 (GPIO 11)
  M    → Pin 21 (GPIO 9,  MISO)
  MO   → Pin 19 (GPIO 10, MOSI)
  NSS  → Pin 24 (GPIO 8,  CE0)
  RST  → Pin 11 (GPIO 17)
  GND  → Pin 6
  5V   → Pin 2  (используй 5V, не 3.3V — встроенный стабилизатор сам понизит)

Подключение I2C:
  SIG IN (SDA) → Pin 3 (GPIO 2)
  SI OUT (SCL) → Pin 5 (GPIO 3)
  IRQ          → Pin 18 (GPIO 24)
  RST          → Pin 11 (GPIO 17)
  GND          → Pin 6
  5V           → Pin 2

Подключение UART:
  SIG IN (TX модуля) → Pin 10 (GPIO 15, RXD)
  SI OUT (RX модуля) → Pin 8  (GPIO 14, TXD)
  RST                → Pin 11 (GPIO 17)
  GND                → Pin 6
  5V                 → Pin 2
"""
import logging
import time
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)

# Попытка импорта Adafruit
try:
    import board
    import busio
    import digitalio
    ADAFRUIT_AVAILABLE = True
except ImportError:
    ADAFRUIT_AVAILABLE = False
    logger.warning("Adafruit CircuitPython не найдена — режим эмуляции.")


class NFCReader:
    """
    Универсальный класс для PN532 на Raspberry Pi 4B.
    Поддерживает SPI, I2C и UART.
    """

    def __init__(
        self,
        interface: str = 'spi',
        rst_pin: int = 17,
        irq_pin: int = 24,
        spi_ce: int = 0,
        uart_port: str = '/dev/serial0',
        uart_baudrate: int = 115200,
    ):
        """
        Args:
            interface:     'spi', 'i2c' или 'uart'
            rst_pin:       GPIO BCM номер пина RST (по умолчанию 17 = Pin 11)
            irq_pin:       GPIO BCM номер пина IRQ (по умолчанию 24 = Pin 18)
            spi_ce:        SPI CE номер: 0 = GPIO8/Pin24, 1 = GPIO7/Pin26
            uart_port:     UART порт ('/dev/serial0' или '/dev/ttyS0')
            uart_baudrate: Скорость UART (115200 по умолчанию)
        """
        self.interface = interface.lower()
        self.rst_pin = rst_pin
        self.irq_pin = irq_pin
        self.spi_ce = spi_ce
        self.uart_port = uart_port
        self.uart_baudrate = uart_baudrate
        self.pn532 = None
        self.initialized = False

    def init(self) -> bool:
        """Инициализация PN532. Возвращает True при успехе."""
        if not ADAFRUIT_AVAILABLE:
            logger.info("NFCReader: режим эмуляции (без железа)")
            self.initialized = True
            return True

        try:
            rst = digitalio.DigitalInOut(getattr(board, f'D{self.rst_pin}'))

            if self.interface == 'spi':
                self.pn532 = self._init_spi(rst)
            elif self.interface == 'i2c':
                self.pn532 = self._init_i2c(rst)
            elif self.interface == 'uart':
                self.pn532 = self._init_uart(rst)
            else:
                raise ValueError(f"Неизвестный интерфейс: {self.interface}")

            version = self.pn532.firmware_version
            logger.info(f"PN532 обнаружен. Прошивка: {version}")
            self.pn532.SAM_configuration()
            self.initialized = True
            return True

        except Exception as e:
            logger.error(f"Ошибка инициализации PN532 ({self.interface}): {e}")
            self.initialized = False
            return False

    def _init_spi(self, rst):
        from adafruit_pn532.spi import PN532_SPI
        spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
        ce_pin = board.D8 if self.spi_ce == 0 else board.D7
        cs = digitalio.DigitalInOut(ce_pin)
        return PN532_SPI(spi, cs, reset=rst, debug=False)

    def _init_i2c(self, rst):
        from adafruit_pn532.i2c import PN532_I2C
        irq = digitalio.DigitalInOut(getattr(board, f'D{self.irq_pin}'))
        irq.direction = digitalio.Direction.INPUT
        i2c = busio.I2C(board.SCL, board.SDA)
        return PN532_I2C(i2c, reset=rst, irq=irq, debug=False)

    def _init_uart(self, rst):
        from adafruit_pn532.uart import PN532_UART
        uart = busio.UART(board.TX, board.RX, baudrate=self.uart_baudrate)
        return PN532_UART(uart, reset=rst, debug=False)

    def read_card_uid(self, timeout: int = 1000) -> Optional[str]:
        """
        Считать UID карты.

        Args:
            timeout: Таймаут в миллисекундах

        Returns:
            UID в hex-формате (например 'A1B2C3D4') или None
        """
        if not self.initialized:
            if not self.init():
                return None

        if not ADAFRUIT_AVAILABLE:
            return None

        try:
            uid = self.pn532.read_passive_target(timeout=timeout / 1000)
            if uid:
                uid_hex = uid.hex().upper()
                logger.info(f"Карта обнаружена: {uid_hex}")
                return uid_hex
            return None
        except Exception as e:
            logger.debug(f"Карта не найдена: {e}")
            return None

    def wait_for_card(self, timeout: int = 0, callback=None) -> Optional[str]:
        """
        Ждать карту в цикле.

        Args:
            timeout:  Таймаут в секундах (0 = бесконечно)
            callback: Вызывается при обнаружении карты: callback(uid)

        Returns:
            UID карты или None при таймауте
        """
        start = time.time()
        while True:
            uid = self.read_card_uid(timeout=500)
            if uid:
                if callback:
                    callback(uid)
                return uid
            if timeout > 0 and (time.time() - start) > timeout:
                return None
            time.sleep(0.1)

    def close(self):
        """Освободить ресурсы."""
        self.initialized = False
        logger.info("NFCReader: закрыт")

    def __enter__(self):
        self.init()
        return self

    def __exit__(self, *_):
        self.close()


def test_nfc(interface: str = 'spi'):
    """Быстрый тест считывателя."""
    logging.basicConfig(level=logging.INFO)
    print(f"Тест PN532 через {interface.upper()}")
    print("Приложите карту... (Ctrl+C для выхода)")

    with NFCReader(interface=interface) as reader:
        if not reader.initialized:
            print("Ошибка инициализации")
            return False
        print("PN532 инициализирован")
        try:
            while True:
                uid = reader.read_card_uid(timeout=500)
                if uid:
                    print(f"Карта: {uid}")
        except KeyboardInterrupt:
            print("Завершение")
    return True


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Тест NFC PN532')
    parser.add_argument('--interface', '-i', default='spi',
                        choices=['spi', 'i2c', 'uart'],
                        help='Интерфейс подключения (по умолчанию: spi)')
    args = parser.parse_args()
    test_nfc(args.interface)
