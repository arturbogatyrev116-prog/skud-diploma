# 🚀 Быстрый старт — NFC интеграция

## 📋 Что нужно

1. **Raspberry Pi** (любая модель с GPIO)
2. **PN532 NFC модуль** (~500-800 ₽)
3. **NFC карты/брелоки** NTAG213/215/216 или Mifare Classic
4. **Провода Dupont** M-F

## 🔧 Подключение (5 минут)

```
PN532          →    Raspberry Pi
─────────────────────────────────────
VCC            →    3.3V (Pin 1)
GND            →    GND (Pin 6)
MOSI           →    GPIO 10 (Pin 19)
MISO           →    GPIO 9  (Pin 21)
SCK            →    GPIO 11 (Pin 23)
NSS/CS         →    GPIO 8  (Pin 24)
IRQ            →    GPIO 25 (Pin 22)  [опционально]
RST            →    GPIO 17 (Pin 11)  [опционально]
```

## ⚡ Установка (10 минут)

```bash
# 1. Клонирование репозитория
cd /home/pi
git clone <your-repo-url> skud-diploma
cd skud-diploma

# 2. Установка зависимостей
sudo chmod +x install_rpi.sh
sudo ./install_rpi.sh

# 3. Перезагрузка
sudo reboot
```

## 🎯 Запуск (2 минуты)

```bash
cd /home/pi/skud-diploma

# Терминал 1: Веб-сервер
./start_web_server.sh

# Терминал 2: NFC сервис (в новом окне)
sudo ./start_nfc_service.sh --zone 1 --auto-register --rank 4
```

Откройте браузер: **http://localhost:5000**

## 📱 Использование

### Вариант 1: Через веб-интерфейс

1. Откройте `http://localhost:5000`
2. В разделе "NFC Считыватель" выберите зону
3. Нажмите "📇 Приложить карту"
4. Приложите NFC-карту к считывателю

### Вариант 2: Через NFC сервис

Сервис автоматически обрабатывает карты:
- ✅ Зелёный свет — доступ разрешён
- 🔴 Красный свет — доступ запрещён
- 🟡 Жёлтый свет — неизвестная карта

## 🔐 Регистрация пользователей

### Автоматически (при поднесении карты)

```bash
sudo ./start_nfc_service.sh --zone 1 --auto-register --rank 4
```

Все новые карты регистрируются с рангом 4.

### Вручную (через веб-интерфейс)

1. Страница "Пользователи" → "Добавить пользователя"
2. Введите UID карты или выберите из списка
3. Установите ранг (3-9)

### Через командную строку

```bash
python3 personalize.py --uid 04A1B2C3 --rank 9 --name "Администратор"
```

## 🛠️ Диагностика

### NFC не работает

```bash
# Проверка SPI
ls /dev/spi*
# Должно быть: /dev/spidev0.0

# Проверка подключения
sudo i2cdetect -y 1

# Перезапуск сервиса
sudo systemctl restart skud-nfc
```

### Посмотреть логи

```bash
# Логи NFC сервиса
sudo journalctl -u skud-nfc -f

# Логи веб-сервера
sudo journalctl -u skud-web -f
```

### Тест NFC

```bash
source venv/bin/activate
python3 test_nfc.py
```

## 📊 Автозапуск при загрузке

```bash
# Установка сервисов
sudo ./install_systemd.sh

# Проверка
sudo systemctl status skud-nfc
sudo systemctl status skud-web

# Включение автозапуска
sudo systemctl enable skud-nfc
sudo systemctl enable skud-web
```

## 📚 Документы

- **README_NFC.md** — подробная инструкция по подключению
- **README.md** — основная документация системы

## ⚡ Команды для быстрого доступа

```bash
# Запустить всё
sudo systemctl start skud-nfc skud-web

# Остановить всё
sudo systemctl stop skud-nfc skud-web

# Перезапустить
sudo systemctl restart skud-nfc skud-web

# Статус
sudo systemctl status skud-nfc skud-web

# Логи в реальном времени
sudo journalctl -u skud-nfc -u skud-web -f
```

---

**Готово!** 🎉 Система работает. Прикладывайте карты для проверки доступа.
