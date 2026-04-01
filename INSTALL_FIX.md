# 🚀 Решение проблемы установки (ОБНОВЛЕНО)

## Ваша ошибка

```
ERROR: Could not find a version that satisfies the requirement pn532>=1.0.0
```

**Причина:** Библиотека `pn532` не опубликована в PyPI.

---

## ✅ Быстрое решение (ИСПРАВЛЕНО)

Используем **официальную библиотеку Adafruit CircuitPython PN532** — поддерживаемое решение с простой установкой.

### Шаг 1: Обновите файлы

Скачайте обновлённые файлы:
- `requirements.txt` — с правильной библиотекой
- `nfc_reader.py` — поддержка Adafruit CircuitPython
- `install_rpi_simple.sh` — обновлённый скрипт

### Шаг 2: Запустите установку

```bash
cd /home/artur/Desktop/skud/skud-diploma

# Очистите старое окружение
rm -rf venv

# Запустите новый скрипт установки
sudo chmod +x install_rpi_simple.sh
sudo ./install_rpi_simple.sh
```

### Шаг 3: Перезагрузитесь

```bash
sudo reboot
```

### Шаг 4: Проверьте работу

```bash
# Тест NFC
source venv/bin/activate
python3 test_nfc.py

# Запуск веб-сервера
./start_web_server.sh
```

Откройте браузер: **http://localhost:5000**

---

## 🔌 Подключение PN532

### I2C (рекомендуется)

```
PN532          →    Raspberry Pi
─────────────────────────────────────
VCC            →    3.3V (Pin 1)
GND            →    GND (Pin 6)
SCL            →    GPIO 3 (Pin 5)
SDA            →    GPIO 2 (Pin 3)
```

### SPI (альтернатива)

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

---

## 📚 Документация

- **README_PN532_ADAFRUIT.md** — подробная инструкция по Adafruit PN532
- **INSTALL_TROUBLESHOOTING.md** — решение всех проблем
- **README_NFC.md** — общая NFC интеграция

---

## 📝 Что изменилось

| Было | Стало |
|------|-------|
| `pn532>=1.0.0` (нет в PyPI) | `adafruit-circuitpython-pn532>=2.3.0` ✅ |
| Самописный код для SPI | Официальная библиотека Adafruit ✅ |
| Проблемы с установкой | `pip install` работает сразу ✅ |

**Итого:** Установка работает через официальную библиотеку Adafruit! 🎉
