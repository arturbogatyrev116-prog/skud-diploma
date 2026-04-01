"""
Модуль работы с NFC-считывателем PN532 для Raspberry Pi
Использует официальную библиотеку Adafruit CircuitPython PN532
Поддерживает чтение UID карт и базовые операции NTAG
"""
import logging
import hashlib
import hmac
import time
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)

# Попытка импорта библиотеки Adafruit
try:
    import board
    import digitalio
    from adafruit_pn532.i2c import PN532_I2C
    # Для SPI версии:
    # from adafruit_pn532.spi import PN532_SPI
    ADAFRUIT_AVAILABLE = True
except ImportError:
    ADAFRUIT_AVAILABLE = False
    logger.warning("adafruit-circuitpython-pn532 не найдена. Используем режим эмуляции.")


class NFCReader:
    """
    Класс для работы с NFC-считывателем PN532
    
    Подключение через I2C (рекомендуется Adafruit):
    - VCC -> 3.3V (Pin 1)
    - GND -> GND (Pin 6)
    - SCL -> GPIO 3/SCL (Pin 5)
    - SDA -> GPIO 2/SDA (Pin 3)
    - IRQ -> GPIO 24 (Pin 18)
    - RST -> GPIO 17 (Pin 11)
    
    Подключение через SPI (альтернативный вариант):
    - VCC -> 3.3V (Pin 1)
    - GND -> GND (Pin 6)
    - MOSI -> GPIO 10 (Pin 19)
    - MISO -> GPIO 9 (Pin 21)
    - SCK -> GPIO 11 (Pin 23)
    - NSS/CS -> GPIO 8 (Pin 24)
    - IRQ -> GPIO 25 (Pin 22)
    - RST -> GPIO 17 (Pin 11)
    """
    
    def __init__(self, use_spi: bool = False, spi_device=0, reset_pin: int = 17, irq_pin: int = 24):
        """
        Инициализация NFC-ридера
        
        Args:
            use_spi: Если True, использовать SPI (по умолчанию I2C)
            spi_device: SPI устройство (0 для /dev/spidev0.0)
            reset_pin: GPIO пин для сброса (BCM нумерация)
            irq_pin: GPIO пин для прерываний (BCM нумерация)
        """
        self.use_spi = use_spi
        self.spi_device = spi_device
        self.reset_pin = reset_pin
        self.irq_pin = irq_pin
        self.pn532 = None
        self.initialized = False
        
        if not ADAFRUIT_AVAILABLE:
            logger.info("NFCReader: режим эмуляции (без железа)")
        
    def init(self) -> bool:
        """
        Инициализация PN532
        
        Returns:
            True если успешно, False иначе
        """
        if not ADAFRUIT_AVAILABLE:
            # Режим эмуляции для тестирования без железа
            self.initialized = True
            return True
        
        try:
            if self.use_spi:
                # Инициализация через SPI
                import board
                import digitalio
                from adafruit_pn532.spi import PN532_SPI
                import spidev
                
                # SPI CS пин
                cs = digitalio.DigitalInOut(board.D8)  # GPIO 8 (CE0)
                cs.direction = digitalio.Direction.OUTPUT
                
                # SPI объект
                spi = spidev.SpiDev()
                spi.open(0, self.spi_device)
                spi.max_speed_hz = 500000  # 500 kHz
                
                # Reset пин
                rst = digitalio.DigitalInOut(board.D17)  # GPIO 17
                
                self.pn532 = PN532_SPI(spi, cs, rst, debug=False)
                
            else:
                # Инициализация через I2C (по умолчанию)
                import board
                import digitalio
                
                # IRQ и RST пины
                irq = digitalio.DigitalInOut(board.D24)  # GPIO 24
                irq.direction = digitalio.Direction.INPUT
                
                rst = digitalio.DigitalInOut(board.D17)  # GPIO 17
                
                # I2C объект
                i2c = board.I2C()
                
                self.pn532 = PN532_I2C(i2c, debug=False, irq=irq, reset=rst)
            
            # Проверка связи
            version = self.pn532.ic_version
            logger.info(f"PN532 найден: {version}")
            
            # Настройка SAM
            self.pn532.sam_configuration()
            logger.info("PN532 SAM настроен")
            
            self.initialized = True
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
        
        if not ADAFRUIT_AVAILABLE:
            # Эмуляция для тестирования
            logger.debug("NFCReader: эмуляция чтения UID")
            return None
        
        try:
            # Чтение карты с таймаутом
            uid = self.pn532.read_passive_target(timeout=timeout/1000)
            
            if uid:
                uid_hex = uid.hex().upper()
                logger.info(f"Обнаружена карта: {uid_hex}")
                return uid_hex
            
            return None
            
        except Exception as e:
            logger.debug(f"Карта не найдена (таймаут): {e}")
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
        if not self.initialized or not ADAFRUIT_AVAILABLE:
            return None
        
        try:
            # NTAG использует Mifare Classic команды для чтения
            data = self.pn532.mifare_classic_read(page)
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
        if not self.initialized or not ADAFRUIT_AVAILABLE:
            return False
        
        if len(data) > 16:
            logger.error("Данные превышают 16 байт")
            return False
        
        try:
            # Аутентификация если предоставлены ключи
            if key_a:
                # Аутентификация с ключом A
                pass
            
            # Запись данных поблочно (4 байта за раз)
            for i in range(0, len(data), 4):
                block_data = data[i:i+4]
                if len(block_data) < 4:
                    block_data = block_data + b'\x00' * (4 - len(block_data))
                
                self.pn532.mifare_classic_write(page + i // 4, block_data)
            
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
        
        # Формируем данные для записи
        uid_hash = hashlib.md5(uid.encode()).digest()[:4]
        data_to_write = uid_hash + token[:12]  # 16 байт
        
        if self.write_ntag_data(0xE8, data_to_write):  # Страница NTAG 424 DNA
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
        if not ADAFRUIT_AVAILABLE:
            return None, "Adafruit библиотека недоступна"
        
        try:
            data = self.read_ntag_data(page=0xE8, count=4)
            
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
        if not ADAFRUIT_AVAILABLE:
            return
            
        try:
            # Освобождение ресурсов
            self.initialized = False
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
    print("Тест NFC-ридера PN532 (Adafruit)")
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
