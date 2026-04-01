# 📡 Интеграция NFC с СКУД на Raspberry Pi

## 📋 Обзор

Данный документ описывает процесс подключения и настройки NFC-считывателя **PN532** для работы с системой СКУД на Raspberry Pi.

## 🔧 Оборудование

### Необходимые компоненты

| Компонент | Описание | Примерная цена |
|-----------|----------|----------------|
| Raspberry Pi 3/4/Zero | Любая модель с GPIO | от 1500 ₽ |
| PN532 NFC модуль | NFC-считыватель/записыватель | ~500-800 ₽ |
| Антенна NFC | Входит в комплект PN532 | - |
| Провода Dupont | M-F для подключения | ~100 ₽ | |
| NFC карты/брелоки | NTAG213/215/216, Mifare Classic | ~50 ₽/шт |

### Альтернативные NFC-ридеры

- **RC522** - более дешёвый вариант (только Mifare Classic)
- **ACR122U** - USB ридер (не требует подключения к GPIO)
- **PN7150** - современная замена PN532

## 📌 Схема подключения PN532 (SPI режим)

### Распиновка PN532 → Raspberry Pi

```
┌─────────────────────────────────────────────────────────────┐
│                    PN532 → Raspberry Pi                      │
├──────────────┬──────────────────┬───────────────────────────┤
│   PN532      │     Raspberry    │      Описание             │
│     Пин      │       Pi         │                           │
├──────────────┼──────────────────┼───────────────────────────┤
│ VCC          │ 3.3V (Pin 1)     │ Питание 3.3V              │
│ GND          │ GND (Pin 6)      │ Земля                     │
│ MOSI         │ GPIO 10 (Pin 19) │ SPI Master Out Slave In   │
│ MISO         │ GPIO 9  (Pin 21) │ SPI Master In Slave Out   │
│ SCK          │ GPIO 11 (Pin 23) │ SPI Clock                 │
│ NSS/CS       │ GPIO 8  (Pin 24) │ SPI Chip Select           │
│ IRQ          │ GPIO 25 (Pin 22) │ Прерывание (опционально)  │
│ RST          │ GPIO 17 (Pin 11) │ Сброс                     │
└──────────────┴──────────────────┴───────────────────────────┘
```

### Визуальная схема

```
     ┌─────────────────┐
     │     PN532       │
     │    NFC Module   │
     │                 │
     │  VCC ───────────┼───────→ 3.3V (Pin 1)
     │  GND ───────────┼───────→ GND (Pin 6)
     │  MOSI ──────────┼───────→ GPIO 10/MOSI (Pin 19)
     │  MISO ──────────┼───────→ GPIO 9/MISO (Pin 21)
     │  SCK ───────────┼───────→ GPIO 11/SCLK (Pin 23)
     │  NSS ───────────┼───────→ GPIO 8/CE0 (Pin 24)
     │  IRQ ───────────┼───────→ GPIO 25 (Pin 22)
     │  RST ───────────┼───────→ GPIO 17 (Pin 11)
     └─────────────────┘
```

### Подключение к Raspberry Pi 4

```
    ┌────────────────────────────────────────┐
    │        Raspberry Pi 4 (GPIO)           │
    │                                        │
    │  [3.3V]  [5V]   [GND]  [5V]           │
    │    ●       ●      ●      ●      ← 3.3V (Pin 1)
    │                                        │
    │  [GPIO2] [GND]  [GPIO3] [GPIO4]        │
    │    ●       ●      ●      ●             │
    │                                        │
    │  [GPIO5] [GND]  [GPIO6] [GPIO7]        │
    │    ●       ●      ●      ●             │
    │                                        │
    │  [GPIO8]●[GND]  [GPIO9]●[GPIO10]●      │  ← CE0, MISO, MOSI
    │                                        │
    │  [GPIO11]●[GND] [GPIO12] [GPIO13]      │  ← SCLK
    │                                        │
    │  ...      ...    ...     ...           │
    │                                        │
    │  [GPIO22]●[GPIO23][GND]  [GPIO24]      │
    │                                        │
    │  [GPIO25]●[GPIO26][GPIO27] [GPIO17]●   │  ← IRQ, RST
    └────────────────────────────────────────┘
```

## 🛠️ Установка ПО

### 1. Запуск скрипта установки

```bash
cd /path/to/skud-diploma
sudo ./install_rpi.sh
```

Скрипт автоматически:
- Обновит систему
- Установит Python 3 и зависимости
- Включит SPI и I2C интерфейсы
- Создаст виртуальное окружение
- Установит библиотеки `pn532`, `spidev`, `RPi.GPIO`

### 2. Ручная установка (опционально)

```bash
# Обновление системы
sudo apt-get update
sudo apt-get upgrade -y

# Установка зависимостей
sudo apt-get install -y python3-pip python3-venv python3-dev libffi-dev libssl-dev spi-tools

# Включение SPI
sudo raspi-config
# Interface Options → SPI → Enable

# Или через командную строку:
sudo sed -i 's/#dtparam=spi=/dtparam=spi=/' /boot/config.txt
echo "dtparam=spi=on" | sudo tee -a /boot/config.txt

# Перезагрузка
sudo reboot
```

### 3. Установка Python библиотек

```bash
# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install --upgrade pip
pip install flask flask-wtf cryptography
pip install pn532 spidev RPi.GPIO
```

## ✅ Проверка работы

### 1. Проверка SPI интерфейса

```bash
# Проверка SPI устройств
ls /dev/spi*
# Должно показать: /dev/spidev0.0  /dev/spidev0.1

# Информация о SPI
sudo i2cdetect -y 0  # Для старых Pi
sudo i2cdetect -y 1  # Для новых Pi
```

### 2. Тест NFC-ридера

```bash
# Активация виртуального окружения
source venv/bin/activate

# Запуск теста
python3 nfc_reader.py
```

Ожидаемый вывод:
```
==================================================
Тест NFC-ридера PN532
==================================================
PN532 версия: {'ver': 1, 'rev': 6, 'support': 0}
✅ PN532 инициализирован

Приложите карту... (Ctrl+C для выхода)
✅ Карта: 04A1B2C3
```

### 3. Тест NFC сервиса

```bash
# Запуск сервиса для зоны "Офис" (зона 1)
sudo python3 nfc_service.py --zone 1

# С авто-регистрацией новых карт
sudo python3 nfc_service.py --zone 1 --auto-register --rank 4
```

### 4. Запуск веб-сервера

```bash
# В одном терминале - веб-сервер
source venv/bin/activate
python3 app.py

# В другом терминале - NFC сервис (опционально)
sudo python3 nfc_service.py --zone 1
```

Откройте браузер: `http://localhost:5000` или `http://<IP_RASPBERRY>:5000`

## 🔧 Настройка systemd сервиса

### 1. Создание сервиса

```bash
sudo nano /etc/systemd/system/skud-nfc.service
```

Содержимое файла:

```ini
[Unit]
Description=СКУД NFC Service
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/skud-diploma
Environment="PATH=/home/pi/skud-diploma/venv/bin"
ExecStart=/home/pi/skud-diploma/venv/bin/python3 /home/pi/skud-diploma/nfc_service.py --zone 1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 2. Активация сервиса

```bash
# Перезагрузка systemd
sudo systemctl daemon-reload

# Включение автозапуска
sudo systemctl enable skud-nfc.service

# Запуск сервиса
sudo systemctl start skud-nfc.service

# Проверка статуса
sudo systemctl status skud-nfc.service

# Просмотр логов
sudo journalctl -u skud-nfc.service -f
```

### 3. Управление сервисом

```bash
# Остановка
sudo systemctl stop skud-nfc.service

# Перезапуск
sudo systemctl restart skud-nfc.service

# Отключение автозапуска
sudo systemctl disable skud-nfc.service
```

## 📱 Использование

### Регистрация пользователя

```bash
# Через командную строку
python3 personalize.py --uid ADMIN_01 --rank 9 --name "Администратор"

# Или через веб-интерфейс
# Страница "Пользователи" → "Добавить пользователя"
```

### Эмуляция прохода через веб-интерфейс

1. Откройте `http://localhost:5000`
2. В разделе "NFC Считыватель" выберите зону
3. Нажмите "📇 Приложить карту"
4. Приложите NFC-карту к считывателю

### Режимы работы NFC сервиса

#### Одиночный опрос (через веб-интерфейс)

```javascript
// POST /api/nfc/poll
{
  "zone_to": 1  // Зона доступа
}
```

#### Фоновый сервис (автономно)

```bash
# Запуск для зоны "Офис"
sudo python3 nfc_service.py --zone 1

# С авто-регистрацией
sudo python3 nfc_service.py --zone 1 --auto-register --rank 4

# Отладочный режим
sudo python3 nfc_service.py --zone 1 --debug
```

## 🐛 Диагностика проблем

### PN532 не определяется

```bash
# Проверка SPI
ls /dev/spi*

# Проверка подключения
sudo i2cdetect -y 1

# Проверка прав доступа
groups pi  # Должна быть группа spi
```

**Решение:**
1. Проверьте подключение проводов
2. Убедитесь что SPI включен: `sudo raspi-config`
3. Добавьте пользователя в группу: `sudo usermod -a -G spi pi`
4. Перезагрузитесь: `sudo reboot`

### Ошибка "Permission denied"

```bash
# Проверка прав на SPI устройство
ls -la /dev/spidev0.0

# Добавление правил udev
sudo nano /etc/udev/rules.d/99-spi.rules
# Добавьте: KERNEL=="spidev*", MODE="0666"

sudo udevadm control --reload-rules
```

### Библиотека pn532 не устанавливается

```bash
# Альтернативная установка
pip install --upgrade pip
pip install pn532 --no-cache-dir

# Или используйте библиотеку Adafruit_PN532
pip install Adafruit_CircuitPython_PN532
```

### Карта не читается

1. Проверьте расстояние (карта должна быть вплотную к антенне)
2. Убедитесь что карта работает на частоте 13.56 MHz
3. Попробуйте другую карту
4. Проверьте что карта не экранирована металлом

## 📊 Архитектура работы

```
┌─────────────────────────────────────────────────────────────┐
│                    СКУД с NFC                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │  NFC Карта  │───▶│   PN532      │───▶│  Raspberry Pi │  │
│  │  (UID)      │    │  (SPI/I2C)   │    │   (GPIO)      │  │
│  └─────────────┘    └──────────────┘    └───────┬───────┘  │
│                                                  │          │
│                                                  ▼          │
│                                         ┌───────────────┐  │
│                                         │  nfc_reader   │  │
│                                         │    (Python)   │  │
│                                         └───────┬───────┘  │
│                                                  │          │
│                    ┌─────────────────────────────┤          │
│                    │                             │          │
│                    ▼                             ▼          │
│         ┌──────────────────┐          ┌──────────────────┐  │
│         │  nfc_service.py  │          │     app.py       │  │
│         │  (фоновый демон) │          │  (веб-сервер)    │  │
│         └────────┬─────────┘          └────────┬─────────┘  │
│                  │                             │            │
│                  └──────────┬──────────────────┘            │
│                             │                               │
│                             ▼                               │
│                  ┌──────────────────┐                       │
│                  │   database.py    │                       │
│                  │   (SQLite БД)    │                       │
│                  └──────────────────┘                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 🔐 Безопасность

### Рекомендации

1. **Храните секретные ключи** в безопасном месте
2. **Используйте NTAG 424 DNA** для защищённых карт
3. **Ограничьте физический доступ** к Raspberry Pi
4. **Включите HTTPS** для веб-интерфейса
5. **Регулярно обновляйте** систему и зависимости

### Настройка брандмауэра

```bash
# Установка ufw
sudo apt-get install ufw

# Разрешение SSH и HTTP
sudo ufw allow 22/tcp
sudo ufw allow 5000/tcp

# Включение брандмауэра
sudo ufw enable
```

## 📈 Расширенные возможности

### Запись данных на NTAG

```python
from nfc_reader import NFCReader

reader = NFCReader()
reader.init()

# Запись данных
data = b'My custom data'
reader.write_ntag_data(page=4, data=data)

# Чтение данных
data = reader.read_ntag_data(page=4, count=4)
print(f"Прочитано: {data.hex()}")
```

### Интеграция с электромагнитным замком

```python
import RPi.GPIO as GPIO

LOCK_PIN = 18  # GPIO пин для реле замка

GPIO.setmode(GPIO.BCM)
GPIO.setup(LOCK_PIN, GPIO.OUT)

def unlock_door():
    """Открыть дверь на 3 секунды"""
    GPIO.output(LOCK_PIN, GPIO.LOW)  # Реле замкнуто
    time.sleep(3)
    GPIO.output(LOCK_PIN, GPIO.HIGH)  # Реле разомкнуто
```

## 📚 Дополнительные ресурсы

- [Документация PN532](https://www.nxp.com/docs/en/user-guide/141520.pdf)
- [SPI на Raspberry Pi](https://www.raspberrypi.org/documentation/hardware/raspberrypi/spi/)
- [RPi.GPIO документация](https://sourceforge.net/p/raspberry-gpio-python/wiki/)

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи: `sudo journalctl -u skud-nfc.service`
2. Запустите в режиме отладки: `python3 nfc_service.py --debug`
3. Проверьте подключение мультиметром
