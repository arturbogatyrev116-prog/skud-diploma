"""
Модуль работы с NFC-считывателем PN532 для Raspberry Pi
Поддерживает чтение UID карт и запись NTAG 424 DNA
"""
import logging
import hashlib
import hmac
import struct
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)

# Попытка импорта библиотеки для PN532
try:
    from pn532 import PN532_SPI, PN532
    PN532_AVAILABLE = True
except ImportError:
    PN532_AVAILABLE = False
    logger.warning("Библиотека pn532 не найдена. Установите: pip install pn532")

# Константы для NTAG 424 DNA
NTAG_424_DNA_PAGE = 0xE8  # Страница для записи защищённых данных
NTAG_AUTH_PAGE = 0xA5     # Страница аутентификации


class NFCReader:
    """
    Класс для работы с NFC-считывателем PN532
    
    Подключение через SPI:
    - VCC -> 3.3V (пин 1)
    - GND -> GND (пин 6)
    - MOSI -> GPIO 10 (пин 19)
    - MISO -> GPIO 9 (пин 21)
    - SCK -> GPIO 11 (пин 23)
    - NSS/CS -> GPIO 8 (пин 24)
    - IRQ -> GPIO 25 (пин 22)
    - RST -> GPIO 17 (пин 11)
    """
    
    def __init__(self, spi_device: int = 0, spi_bus: int = 0, reset_pin: int = 17, irq_pin: int = 25):
        """
        Инициализация NFC-ридера
        
        Args:
            spi_device: SPI устройство (0 для /dev/spidev0.0)
            spi_bus: SPI шина (0 для Raspberry Pi)
            reset_pin: GPIO пин для сброса (BCM нумерация)
            irq_pin: GPIO пин для прерываний (BCM нумерация)
        """
        self.spi_device = spi_device
        self.spi_bus = spi_bus
        self.reset_pin = reset_pin
        self.irq_pin = irq_pin
        self.reader: Optional[PN532_SPI] = None
        self.initialized = False
        
        if not PN532_AVAILABLE:
            logger.error("Библиотека pn532 недоступна. Используем режим эмуляции.")
        
    def init(self) -> bool:
        """
        Инициализация PN532
        
        Returns:
            True если успешно, False иначе
        """
        if not PN532_AVAILABLE:
            # Режим эмуляции для тестирования без железа
            logger.info("PN532: эмуляция инициализации (режим без железа)")
            self.initialized = True
            return True
            
        try:
            import spidev
            import RPi.GPIO as GPIO
            
            # Настройка SPI
            spi = spidev.SpiDev()
            spi.open(self.spi_bus, self.spi_device)
            spi.max_speed_hz = 500000  # 500 kHz
            
            # Настройка GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.reset_pin, GPIO.OUT)
            GPIO.setup(self.irq_pin, GPIO.IN)
            
            # Создание объекта PN532
            self.reader = PN532_SPI(spi, self.reset_pin, self.irq_pin)
            
            # Проверка связи
            version = self.reader.get_version()
            logger.info(f"PN532 версия: {version}")
            
            # Настройка антенны
            self.reader.set_passive_activation_mode(True)
            
            self.initialized = True
            logger.info("PN532 успешно инициализирован")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка инициализации PN532: {e}")
            self.initialized = False
            return False
    
    def read_card_uid(self, timeout: int = 1000) -> Optional[str]:
        """
        Считать UID карты
        
        Args:
            timeout: Таймаут в миллисекундах
            
        Returns:
            UID карты в hex-формате или None если карта не найдлена
        """
        if not self.initialized:
            if not self.init():
                return None
        
        if not PN532_AVAILABLE:
            # Эмуляция для тестирования
            logger.debug("PN532: эмуляция чтения UID")
            return None
        
        try:
            # Чтение карты в режиме MiFare Classic
            uid = self.reader.read_passive_target(timeout)
            
            if uid:
                uid_hex = uid.hex().upper()
                logger.info(f"Обнаружена карта: {uid_hex}")
                return uid_hex
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка чтения UID: {e}")
            return None
    
    def read_ntag_data(self, page: int = 4, count: int = 4) -> Optional[bytes]:
        """
        Прочитать данные из NTAG карты
        
        Args:
            page: Начальная страница для чтения
            count: Количество страниц для чтения (1 страница = 4 байта)
            
        Returns:
            Прочитанные данные или None
        """
        if not self.initialized:
            return None
            
        if not PN532_AVAILABLE:
            return None
        
        try:
            # Аутентификация не требуется для публичных страниц NTAG
            data = self.reader.mifare_classic_read(page)
            logger.debug(f"NTAG данные со страницы {page}: {data.hex()}")
            return data
            
        except Exception as e:
            logger.error(f"Ошибка чтения NTAG: {e}")
            return None
    
    def write_ntag_data(
        self, 
        page: int, 
        data: bytes, 
        key_a: bytes = None,
        key_b: bytes = None
    ) -> bool:
        """
        Записать данные в NTAG карту
        
        Args:
            page: Страница для записи
            data: Данные для записи (максимум 16 байт)
            key_a: Ключ A для аутентификации (опционально)
            key_b: Ключ B для аутентификации (опционально)
            
        Returns:
            True если успешно, False иначе
        """
        if not self.initialized:
            return False
            
        if not PN532_AVAILABLE:
            return False
        
        if len(data) > 16:
            logger.error("Данные превышают 16 байт")
            return False
        
        try:
            # Аутентификация если предоставлены ключи
            if key_a:
                # Аутентификация с ключом A
                pass  # Реализация зависит от типа карты
            
            # Запись данных
            # Для NTAG запись поблочная (4 байта за раз)
            for i in range(0, len(data), 4):
                block_data = data[i:i+4]
                # Дополняем до 4 байт если нужно
                if len(block_data) < 4:
                    block_data = block_data + b'\x00' * (4 - len(block_data))
                
                self.reader.mifare_classic_write(page + i // 4, block_data)
            
            logger.info(f"NTAG: записано {len(data)} байт на страницу {page}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка записи NTAG: {e}")
            return False
    
    def write_protected_data(
        self, 
        uid: str, 
        secret_key: bytes,
        history: list
    ) -> Tuple[bool, str]:
        """
        Записать защищённые данные на NTAG 424 DNA
        
        Использует HMAC-SHA256 для создания защитного токена.
        
        Args:
            uid: UID пользователя
            secret_key: Секретный ключ пользователя
            history: История перемещений
            
        Returns:
            (success, message)
        """
        import json
        
        # Создаём токен аутентификации
        history_bytes = json.dumps(history).encode()
        token = hmac.new(secret_key, history_bytes, hashlib.sha256).digest()
        
        # Формируем данные для записи:
        # [4 байта UID hash][16 байт HMAC][4 байта timestamp]
        uid_hash = hashlib.md5(uid.encode()).digest()[:4]
        timestamp = struct.pack('>I', int(hashlib.sha256(history_bytes).digest()[:4], 16) & 0xFFFFFFFF)
        
        data_to_write = uid_hash + token[:12]  # 16 байт всего
        
        if self.write_ntag_data(NTAG_424_DNA_PAGE, data_to_write):
            logger.info(f"NTAG 424 DNA: записаны защищённые данные для {uid}")
            return True, "Данные записаны"
        else:
            return False, "Ошибка записи"
    
    def read_protected_data(self) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Прочитать защищённые данные с NTAG 424 DNA
        
        Returns:
            (data_dict, message)
        """
        if not PN532_AVAILABLE:
            return None, "PN532 недоступен"
        
        try:
            data = self.read_ntag_data(NTAG_424_DNA_PAGE, 4)
            
            if not data or len(data) < 16:
                return None, "Недостаточно данных"
            
            uid_hash = data[:4]
            hmac_token = data[4:16]
            
            return {
                'uid_hash': uid_hash.hex(),
                'hmac': hmac_token.hex()
            }, "Данные прочитаны"
            
        except Exception as e:
            logger.error(f"Ошибка чтения защищённых данных: {e}")
            return None, str(e)
    
    def wait_for_card(self, timeout: int = 0, callback=None) -> Optional[str]:
        """
        Ждать карту в бесконечном цикле
        
        Args:
            timeout: Таймаут в секундах (0 = бесконечно)
            callback: Функция обратного вызова при обнаружении карты
            
        Returns:
            UID карты или None
        """
        import time
        
        start_time = time.time()
        
        while True:
            uid = self.read_card_uid(timeout=500)
            
            if uid:
                logger.info(f"Карта обнаружена: {uid}")
                if callback:
                    callback(uid)
                return uid
            
            if timeout > 0 and (time.time() - start_time) > timeout:
                logger.debug("Таймаут ожидания карты")
                return None
            
            time.sleep(0.1)
    
    def close(self):
        """Закрыть соединение с PN532"""
        if not PN532_AVAILABLE:
            return
            
        try:
            import RPi.GPIO as GPIO
            GPIO.cleanup()
            logger.info("PN532: соединение закрыто")
        except Exception as e:
            logger.error(f"Ошибка закрытия: {e}")
    
    def __enter__(self):
        self.init()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Функция для быстрого тестирования
def test_nfc():
    """Тест NFC-ридера"""
    print("=" * 50)
    print("Тест NFC-ридера PN532")
    print("=" * 50)
    
    reader = NFCReader()
    
    if not reader.init():
        print("❌ Ошибка инициализации PN532")
        return False
    
    print("✅ PN532 инициализирован")
    print("\nПриложите карту... (Ctrl+C для выхода)")
    
    try:
        while True:
            uid = reader.read_card_uid(timeout=500)
            if uid:
                print(f"✅ Карта: {uid}")
                
                # Попытка прочитать данные NTAG
                data = reader.read_ntag_data(page=4, count=4)
                if data:
                    print(f"   Данные NTAG: {data.hex()}")
    except KeyboardInterrupt:
        print("\nЗавершение...")
    finally:
        reader.close()
    
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_nfc()
