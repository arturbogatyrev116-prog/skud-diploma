#!/bin/bash
# Упрощённый скрипт установки СКУД на Raspberry Pi
# Работает без pn532 библиотеки - используем прямую SPI связь

set -e

echo "============================================================"
echo "  Установка СКУД на Raspberry Pi"
echo "============================================================"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

if [ "$EUID" -ne 0 ]; then 
    log_error "Запустите через sudo: sudo $0"
    exit 1
fi

log_info "Обновление пакетов..."
apt-get update

log_info "Установка системных зависимостей..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    libffi-dev \
    libssl-dev \
    build-essential \
    git \
    spi-tools \
    i2c-tools

# Включение SPI
log_info "Включение SPI..."
if ! grep -q "dtparam=spi=on" /boot/config.txt; then
    echo "dtparam=spi=on" >> /boot/config.txt
    log_info "SPI включён (нужна перезагрузка)"
else
    log_info "SPI уже включён"
fi

# Включение I2C
log_info "Включение I2C..."
if ! grep -q "dtparam=i2c_arm=on" /boot/config.txt; then
    echo "dtparam=i2c_arm=on" >> /boot/config.txt
else
    log_info "I2C уже включён"
fi

# Добавление в группы
usermod -a -G spi ${SUDO_USER:-pi} 2>/dev/null || true
usermod -a -G i2c ${SUDO_USER:-pi} 2>/dev/null || true

# Виртуальное окружение
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"

log_info "Создание venv в $VENV_DIR..."
python3 -m venv "$VENV_DIR"

log_info "Активация venv..."
source "$VENV_DIR/bin/activate"

log_info "Обновление pip..."
pip install --upgrade pip

log_info "Установка Python зависимостей..."
pip install -r "$PROJECT_DIR/requirements.txt"

# Проверка установки
log_info "Проверка установленных пакетов..."
python3 -c "from adafruit_pn532.i2c import PN532_I2C; print('adafruit-pn532: OK')" 2>/dev/null || log_warn "adafruit-pn532: не установлен"
python3 -c "import spidev; print('spidev: OK')" 2>/dev/null || log_warn "spidev: не установлен"
python3 -c "import RPi.GPIO; print('RPi.GPIO: OK')" 2>/dev/null || log_warn "RPi.GPIO: не установлен"
python3 -c "import flask; print('flask: OK')"
python3 -c "import cryptography; print('cryptography: OK')"

# Создаём скрипты запуска
log_info "Создание скриптов запуска..."

cat > "$PROJECT_DIR/start_web_server.sh" << 'EOF'
#!/bin/bash
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$PROJECT_DIR/venv/bin/activate"
cd "$PROJECT_DIR"
python3 app.py
EOF
chmod +x "$PROJECT_DIR/start_web_server.sh"

cat > "$PROJECT_DIR/start_nfc_service.sh" << 'EOF'
#!/bin/bash
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$PROJECT_DIR/venv/bin/activate"
cd "$PROJECT_DIR"
python3 nfc_service.py "$@"
EOF
chmod +x "$PROJECT_DIR/start_nfc_service.sh"

deactivate

log_info "============================================================"
log_info "  Установка завершена!"
log_info "============================================================"
echo ""
echo "  Далее:"
echo "  1. Перезагрузитесь: sudo reboot"
echo "  2. Подключите PN532 (см. README_NFC.md)"
echo "  3. Запустите: ./start_web_server.sh"
echo "  4. В другом терминале: sudo ./start_nfc_service.sh --zone 1"
echo ""
