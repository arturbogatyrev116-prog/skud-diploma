# 🔧 Решение проблем установки на Raspberry Pi

## ❌ Ошибка: `cryptography` требует Rust

**Симптомы:**
```
error: subprocess-exited-with-error
Preparing metadata (pyproject.toml) did not run successfully.
Target triple not supported by rustup: i386-unknown-linux-gnu
```

**Решение 1: Установить Rust**
```bash
# Установка Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source $HOME/.cargo/env

# Попытка установки снова
sudo ./install_rpi.sh
```

**Решение 2: Использовать упрощённый скрипт**
```bash
# Скачайте обновлённый скрипт
sudo chmod +x install_rpi_simple.sh
sudo ./install_rpi_simple.sh
```

---

## ❌ Ошибка: `pn532>=1.0.0` не найден

**Симптомы:**
```
ERROR: Could not find a version that satisfies the requirement pn532>=1.0.0
ERROR: No matching distribution found for pn532>=1.0.0
```

**Решение:**
Библиотека `pn532` не опубликована в PyPI. Используйте обновлённый код:

```bash
# Обновите requirements.txt (уже сделано в новой версии)
# pn532 удалён из зависимостей

# Используйте прямую SPI связь через spidev
sudo ./install_rpi_simple.sh
```

---

## ❌ Ошибка: `spidev` не устанавливается

**Симптомы:**
```
error: Can not find the SPI device
```

**Решение:**
```bash
# Включите SPI через raspi-config
sudo raspi-config
# Interface Options → SPI → Enable

# Или вручную
sudo sed -i 's/#dtparam=spi=/dtparam=spi=/' /boot/config.txt
echo "dtparam=spi=on" | sudo tee -a /boot/config.txt

# Перезагрузка
sudo reboot
```

---

## ❌ Ошибка: `RPi.GPIO` не находится

**Симптомы:**
```
ModuleNotFoundError: No module named 'RPi.GPIO'
```

**Решение:**
```bash
# Установка системной версии
sudo apt-get install -y python3-rpi.gpio

# Или через pip
pip install RPi.GPIO
```

---

## ❌ PN532 не определяется

**Симптомы:**
```
PN532 не найден
Ошибка инициализации PN532
```

**Проверка подключения:**

1. **Проверьте SPI устройства:**
```bash
ls /dev/spi*
# Должно быть: /dev/spidev0.0  /dev/spidev0.1
```

2. **Проверьте подключение проводов:**
```
PN532          →    Raspberry Pi
─────────────────────────────────────
VCC            →    3.3V (Pin 1)     ← Проверьте напряжение!
GND            →    GND (Pin 6)
MOSI           →    GPIO 10 (Pin 19)
MISO           →    GPIO 9  (Pin 21)
SCK            →    GPIO 11 (Pin 23)
NSS/CS         →    GPIO 8  (Pin 24)
```

3. **Проверьте права доступа:**
```bash
# Добавьте пользователя в группу spi
sudo usermod -a -G spi pi
sudo usermod -a -G i2c pi

# Проверьте группы
groups pi
```

4. **Тест SPI:**
```bash
# Установите spi-tools
sudo apt-get install spi-tools

# Тест
sudo spidev_test -D /dev/spidev0.0
```

---

## ❌ Карта не читается

**Симптомы:**
```
Карта не обнаружена
UID: None
```

**Решение:**

1. **Проверьте расстояние** — карта должна быть вплотную к антенне
2. **Попробуйте другую карту** — не все карты работают с PN532
3. **Проверьте тип карты** — нужны NTAG213/215/216 или Mifare Classic
4. **Уберите металлические предметы** — металл экранирует сигнал

---

##  Быстрое восстановление

Если всё сломалось, выполните по порядку:

```bash
# 1. Очистка
cd /home/artur/Desktop/skud/skud-diploma
rm -rf venv
sudo rm -rf /root/.cache/pip

# 2. Обновление системы
sudo apt-get update
sudo apt-get upgrade -y

# 3. Установка зависимостей
sudo apt-get install -y python3-pip python3-venv python3-dev \
    libffi-dev libssl-dev build-essential spi-tools i2c-tools

# 4. Включение интерфейсов
sudo raspi-config nonint do_spi 0
sudo raspi-config nonint do_i2c 0

# 5. Перезагрузка
sudo reboot

# 6. Установка проекта
cd /home/artur/Desktop/skud/skud-diploma
sudo ./install_rpi_simple.sh

# 7. Тест
source venv/bin/activate
python3 test_nfc.py
```

---

## 🆘 Если ничего не помогает

### Режим эмуляции (без железа)

Система будет работать в режиме эмуляции для тестирования:

```bash
# Запуск без NFC
./start_web_server.sh

# Используйте ручной ввод UID в веб-интерфейсе
```

### Ручная установка зависимостей

```bash
# Создание venv
python3 -m venv venv
source venv/bin/activate

# Установка по одной
pip install flask==3.0.0
pip install cryptography==42.0.0
pip install flask-wtf==1.2.2
pip install spidev==3.5
pip install RPi.GPIO==0.7.0

# Проверка
python3 -c "import flask; import cryptography; print('OK')"
```

### Проверка без PN532

```bash
# Тест веб-сервера без NFC
source venv/bin/activate
python3 app.py

# Откройте http://localhost:5000
# Используйте ручной ввод UID
```

---

## 📞 Контакты для помощи

Если проблема не решена:

1. Проверьте логи: `sudo journalctl -xe`
2. Запустите в режиме отладки: `python3 app.py --debug`
3. Проверьте `dmesg | grep spi` для диагностики SPI
