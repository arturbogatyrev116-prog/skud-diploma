# 📡 Подключение PN532 с библиотекой Adafruit

## 🎯 Почему Adafruit CircuitPython?

**Официальная поддерживаемая библиотека** с простыми API:
- ✅ Лёгкая установка через pip
- ✅ Поддержка I2C и SPI
- ✅ Хорошая документация
- ✅ Регулярные обновления

---

## 🔌 Подключение I2C (рекомендуется)

**Проще и надёжнее** — меньше проводов, не требует настройки SPI.

```
PN532          →    Raspberry Pi
─────────────────────────────────────
VCC            →    3.3V (Pin 1)
GND            →    GND (Pin 6)
SCL            →    GPIO 3/SCL (Pin 5)
SDA            →    GPIO 2/SDA (Pin 3)
IRQ            →    GPIO 24 (Pin 18)  [опционально]
RST            →    GPIO 17 (Pin 11)  [опционально]
```

### Включение I2C

```bash
# Через raspi-config
sudo raspi-config
# Interface Options → I2C → Enable

# Или вручную
echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt
sudo reboot
```

### Проверка I2C

```bash
# Установка i2c-tools
sudo apt-get install i2c-tools -y

# Сканирование шины
sudo i2cdetect -y 1

# Должно показать адрес PN532 (обычно 0x24)
```

---

## 🔌 Подключение SPI (альтернатива)

**Быстрее** — подходит для частых операций чтения/записи.

```
PN532          →    Raspberry Pi
─────────────────────────────────────
VCC            →    3.3V (Pin 1)
GND            →    GND (Pin 6)
MOSI           →    GPIO 10 (Pin 19)
MISO           →    GPIO 9  (Pin 21)
SCK            →    GPIO 11 (Pin 23)
NSS/CS         →    GPIO 8  (Pin 24)
IRQ            →    GPIO 25 (Pin 22)
RST            →    GPIO 17 (Pin 11)
```

### Включение SPI

```bash
# Через raspi-config
sudo raspi-config
# Interface Options → SPI → Enable

# Или вручную
echo "dtparam=spi=on" | sudo tee -a /boot/config.txt
sudo reboot
```

### Проверка SPI

```bash
# Проверка устройств
ls /dev/spi*
# Должно быть: /dev/spidev0.0  /dev/spidev0.1
```

---

## 🚀 Установка

### Быстрая установка

```bash
cd /home/artur/Desktop/skud/skud-diploma

# Очистка старого окружения
rm -rf venv

# Запуск нового скрипта установки
sudo chmod +x install_rpi_simple.sh
sudo ./install_rpi_simple.sh

# Перезагрузка
sudo reboot
```

### Ручная установка (если нужно)

```bash
# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install adafruit-circuitpython-pn532
pip install adafruit-circuitpython-busdevice
pip install spidev RPi.GPIO
```

---

## 🧪 Тестирование

### Проверка подключения

```bash
cd /home/artur/Desktop/skud/skud-diploma
source venv/bin/activate

# Тест NFC
python3 test_nfc.py
```

**Ожидаемый вывод:**
```
==================================================
Тест NFC-ридера PN532 (Adafruit)
==================================================
PN532 найден: (1, 6, 0)
✅ PN532 инициализирован

Приложите карту... (Ctrl+C для выхода)
✅ Карта: 04A1B2C3
```

### Запуск NFC сервиса

```bash
# Для зоны "Офис" (зона 1)
sudo python3 nfc_service.py --zone 1

# С авто-регистрацией карт
sudo python3 nfc_service.py --zone 1 --auto-register --rank 4
```

### Запуск веб-сервера

```bash
# Веб-интерфейс
./start_web_server.sh

# Откройте: http://localhost:5000
```

---

## 🔧 Настройка в коде

### Использование I2C (по умолчанию)

```python
from nfc_reader import NFCReader

reader = NFCReader(use_spi=False)  # I2C
reader.init()

uid = reader.read_card_uid(timeout=1000)
print(f"UID: {uid}")
```

### Использование SPI

```python
from nfc_reader import NFCReader

reader = NFCReader(use_spi=True, spi_device=0)  # SPI
reader.init()

uid = reader.read_card_uid(timeout=1000)
print(f"UID: {uid}")
```

---

## 🐛 Диагностика

### PN532 не найден

**I2C:**
```bash
# Проверка адреса
sudo i2cdetect -y 1

# Должно показать: 24 на позиции 0x24
```

**SPI:**
```bash
# Проверка устройств
ls /dev/spi*

# Проверка прав
ls -la /dev/spidev0.0
# Должно быть: crw-rw---- 1 root spi ...
```

**Решение:**
```bash
# Добавить пользователя в группу spi
sudo usermod -a -G spi pi
sudo usermod -a -G i2c pi

# Перезагрузка
sudo reboot
```

### Ошибка: "ImportError: No module named 'adafruit_pn532'"

```bash
# Проверка установки
source venv/bin/activate
pip list | grep adafruit

# Переустановка
pip uninstall adafruit-circuitpython-pn532
pip install adafruit-circuitpython-pn532
```

### Ошибка: "RuntimeError: No I2C device found"

**Причины:**
1. I2C не включён
2. Неправильное подключение
3. PN532 не получает питание

**Решение:**
```bash
# Проверка I2C
sudo i2cdetect -y 1

# Проверка напряжения на VCC
# Должно быть 3.3V
```

---

## 📚 Полезные ссылки

- [Adafruit PN532 Documentation](https://docs.circuitpython.org/projects/pn532/en/latest/)
- [CircuitPython on Raspberry Pi](https://learn.adafruit.com/circuitpython-on-raspberry-pi)
- [PN532 Datasheet](https://www.nxp.com/docs/en/user-guide/141520.pdf)

---

## ✅ Чек-лист подключения

- [ ] I2C или SPI включён в raspi-config
- [ ] Провода подключены правильно
- [ ] Питание 3.3V (не 5V!)
- [ ] Скрипт установки выполнен
- [ ] `sudo i2cdetect -y 1` показывает устройство
- [ ] `python3 test_nfc.py` находит карту

**Готово!** 🎉
