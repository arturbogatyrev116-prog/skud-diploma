# 📡 NFC Интеграция — Полное Руководство

## 🚀 Быстрый старт

### 1. Установка

```bash
cd /path/to/skud-diploma
sudo ./install.sh
sudo reboot
```

### 2. Подключение PN532

**I2C (рекомендуется):**
```
PN532          →    Raspberry Pi
─────────────────────────────────────
VCC            →    3.3V (Pin 1)
GND            →    GND (Pin 6)
SCL            →    GPIO 3 (Pin 5)
SDA            →    GPIO 2 (Pin 3)
```

**SPI (альтернатива):**
```
PN532          →    Raspberry Pi
─────────────────────────────────────
VCC            →    3.3V (Pin 1)
GND            →    GND (Pin 6)
MOSI           →    GPIO 10 (Pin 19)
MISO           →    GPIO 9  (Pin 21)
SCK            →    GPIO 11 (Pin 23)
NSS/CS         →    GPIO 8  (Pin 24)
```

### 3. Запуск

```bash
# Веб-сервер + NFC
./start.sh --nfc

# Только веб-сервер
./start_web.sh

# Только NFC (в другом терминале)
sudo ./start_nfc.sh --zone 1
```

Откройте: **http://localhost:5000**

---

## 📋 Оглавление

1. [Оборудование](#оборудование)
2. [Установка](#установка)
3. [Подключение](#подключение)
4. [Использование](#использование)
5. [Диагностика](#диагностика)

---

## Оборудование

### Необходимые компоненты

| Компонент | Описание | Цена |
|-----------|----------|------|
| Raspberry Pi 3/4/Zero | Любая модель с GPIO | от 1500 ₽ |
| PN532 NFC модуль | NFC-считыватель | ~500-800 ₽ |
| NFC карты/брелоки | NTAG213/215/216, Mifare Classic | ~50 ₽/шт |
| Провода Dupont | M-F для подключения | ~100 ₽ |

### Поддерживаемые устройства

| Устройство | Статус | Интерфейс |
|------------|--------|-----------|
| **PN532** | ✅ Полная | I2C, SPI |
| RC522 | ❌ Не поддерживается | - |
| ACR122U | ❌ Не поддерживается | - |

---

## Установка

### Автоматическая установка

```bash
# Скрипт установит все зависимости
sudo ./install.sh

# Перезагрузка
sudo reboot
```

### Ручная установка

```bash
# Системные зависимости
sudo apt-get install -y python3-pip python3-venv python3-dev \
    libffi-dev libssl-dev build-essential spi-tools i2c-tools

# Включение интерфейсов
sudo raspi-config nonint do_spi 0
sudo raspi-config nonint do_i2c 0

# Python зависимости
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Подключение

### Включение I2C

```bash
# Через raspi-config
sudo raspi-config
# Interface Options → I2C → Enable

# Проверка
sudo i2cdetect -y 1
# Должно показать адрес PN532 (0x24)
```

### Включение SPI

```bash
# Через raspi-config
sudo raspi-config
# Interface Options → SPI → Enable

# Проверка
ls /dev/spi*
# Должно быть: /dev/spidev0.0
```

### Настройка в коде

**I2C (по умолчанию):**
```python
from nfc_reader import NFCReader
reader = NFCReader(use_spi=False)
reader.init()
```

**SPI:**
```python
from nfc_reader import NFCReader
reader = NFCReader(use_spi=True)
reader.init()
```

---

## Использование

### Веб-интерфейс

1. Откройте `http://localhost:5000`
2. В разделе "NFC Считыватель" выберите зону
3. Нажмите "📇 Приложить карту"
4. Приложите NFC-карту

### NFC Сервис

```bash
# Запуск для зоны "Офис"
sudo ./start_nfc.sh --zone 1

# С авто-регистрацией
sudo ./start_nfc.sh --zone 1 --auto-register --rank 4

# Отладочный режим
sudo ./start_nfc.sh --zone 1 --debug
```

### Регистрация пользователей

```bash
# Через CLI
python3 personalize.py --uid ADMIN_01 --rank 9 --name "Администратор"

# Или через веб-интерфейс
# Страница "Пользователи" → "Добавить пользователя"
```

### Тестирование

```bash
source venv/bin/activate
python3 test_nfc.py
```

---

## Диагностика

### PN532 не определяется

**I2C:**
```bash
sudo i2cdetect -y 1
# Должно показать: 24 на позиции 0x24
```

**SPI:**
```bash
ls /dev/spi*
# Должно быть: /dev/spidev0.0
```

**Решение:**
```bash
# Добавить в группы
sudo usermod -a -G spi pi
sudo usermod -a -G i2c pi
sudo reboot
```

### Ошибка: "No module named 'adafruit_pn532'"

```bash
source venv/bin/activate
pip install adafruit-circuitpython-pn532
```

### Карта не читается

1. Проверьте расстояние (карта вплотную к антенне)
2. Попробуйте другую карту (NTAG213/215/216)
3. Уберите металлические предметы

### Просмотр логов

```bash
# systemd сервисы
sudo journalctl -u skud-nfc -f
sudo journalctl -u skud-web -f

# Автостарт сервисов
sudo ./install_systemd.sh
```

---

## API Endpoints

### NFC API

```
GET  /api/nfc/status    # Проверка доступности NFC
POST /api/nfc/read      # Чтение UID карты
POST /api/nfc/poll      # Опрос и обработка доступа
```

### Пример запроса

```bash
curl -X POST http://localhost:5000/api/nfc/poll \
  -H "Content-Type: application/json" \
  -d '{"zone_to": 1}'
```

---

## 📚 Документы

- **README.md** — основная документация системы
- **docs/NFC.md** — это руководство (полная версия)
- **docs/TROUBLESHOOTING.md** — решение проблем

---

**Готово!** 🎉 Система работает.
