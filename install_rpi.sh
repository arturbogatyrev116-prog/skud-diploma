#!/bin/bash
# Скрипт установки зависимостей для СКУД с NFC на Raspberry Pi
# Запускать от root или через sudo

set -e

echo "============================================================"
echo "  Установка зависимостей СКУД + NFC для Raspberry Pi"
echo "============================================================"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка что скрипт запущен от root
if [ "$EUID" -ne 0 ]; then 
    log_error "Запустите скрипт через sudo: sudo $0"
    exit 1
fi

log_info "Обновление списка пакетов..."
apt-get update

# Установка системных зависимостей
log_info "Установка системных зависимостей..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    libffi-dev \
    libssl-dev \
    git \
    spi-tools \
    i2c-tools

# Включение SPI интерфейса
log_info "Включение SPI интерфейса..."
if ! grep -q "dtparam=spi=on" /boot/config.txt; then
    echo "dtparam=spi=on" >> /boot/config.txt
    log_info "SPI включён (требуется перезагрузка)"
else
    log_info "SPI уже включён"
fi

# Включение I2C интерфейса (опционально для PN532)
log_info "Включение I2C интерфейса..."
if ! grep -q "dtparam=i2c_arm=on" /boot/config.txt; then
    echo "dtparam=i2c_arm=on" >> /boot/config.txt
    log_info "I2C включён (требуется перезагрузка)"
else
    log_info "I2C уже включён"
fi

# Добавление пользователя в группы spi и i2c
log_info "Добавление пользователя в группы spi и i2c..."
usermod -a -G spi pi 2>/dev/null || usermod -a -G spi $(who | awk '{print $1}' | head -n1)
usermod -a -G i2c pi 2>/dev/null || usermod -a -G i2c $(who | awk '{print $1}' | head -n1)

# Создание виртуального окружения
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"

log_info "Создание виртуального окружения в $VENV_DIR..."
python3 -m venv "$VENV_DIR"

# Активация виртуального окружения
log_info "Активация виртуального окружения..."
source "$VENV_DIR/bin/activate"

# Обновление pip
log_info "Обновление pip..."
pip install --upgrade pip

# Установка Python зависимостей
log_info "Установка Python зависимостей..."
pip install -r "$PROJECT_DIR/requirements.txt"

# Установка библиотеки для PN532
log_info "Установка библиотеки pn532..."
pip install pn532

# Установка spidev для SPI связи
log_info "Установка spidev..."
pip install spidev

# Установка RPi.GPIO для работы с GPIO
log_info "Установка RPi.GPIO..."
pip install RPi.GPIO

# Проверка установки
log_info "Проверка установленных пакетов..."
python3 -c "import pn532; print('pn532: OK')" || log_warn "pn532: не установлен"
python3 -c "import spidev; print('spidev: OK')" || log_warn "spidev: не установлен"
python3 -c "import RPi.GPIO; print('RPi.GPIO: OK')" || log_warn "RPi.GPIO: не установлен"
python3 -c "import flask; print('flask: OK')"
python3 -c "import cryptography; print('cryptography: OK')"

# Создание скрипта запуска
log_info "Создание скрипта запуска start_nfc_service.sh..."
cat > "$PROJECT_DIR/start_nfc_service.sh" << 'EOF'
#!/bin/bash
# Скрипт запуска NFC сервиса

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"

# Активация виртуального окружения
source "$VENV_DIR/bin/activate"

# Запуск сервиса
cd "$PROJECT_DIR"
python3 nfc_service.py "$@"
EOF
chmod +x "$PROJECT_DIR/start_nfc_service.sh"

# Создание скрипта запуска веб-сервера
log_info "Создание скрипта запуска start_web_server.sh..."
cat > "$PROJECT_DIR/start_web_server.sh" << 'EOF'
#!/bin/bash
# Скрипт запуска веб-сервера СКУД

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"

# Активация виртуального окружения
source "$VENV_DIR/bin/activate"

# Запуск сервера
cd "$PROJECT_DIR"
python3 app.py
EOF
chmod +x "$PROJECT_DIR/start_web_server.sh"

# Деактивация виртуального окружения
deactivate

log_info "============================================================"
log_info "  Установка завершена!"
log_info "============================================================"
echo ""
echo "  Следующие шаги:"
echo "  1. Перезагрузите Raspberry Pi: sudo reboot"
echo "  2. Подключите PN532 согласно схеме (см. README_NFC.md)"
echo "  3. Запустите веб-сервер: ./start_web_server.sh"
echo "  4. Запустите NFC сервис: sudo ./start_nfc_service.sh --zone 1"
echo ""
echo "  Или установите systemd сервис:"
echo "  sudo ./install_systemd.sh"
echo "============================================================"
