#!/bin/bash
# Скрипт установки systemd сервисов для СКУД
# Запускать от root или через sudo

set -e

echo "============================================================"
echo "  Установка systemd сервисов СКУД"
echo "============================================================"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

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

# Определение директории проекта
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_NAME="${SUDO_USER:-$(whoami)}"
HOME_DIR="/home/$USER_NAME"

log_info "Директория проекта: $PROJECT_DIR"
log_info "Пользователь: $USER_NAME"

# Проверка виртуального окружения
VENV_DIR="$PROJECT_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
    log_error "Виртуальное окружение не найдено в $VENV_DIR"
    log_error "Запустите сначала install_rpi.sh"
    exit 1
fi

# Создание сервиса NFC
log_info "Создание сервиса skud-nfc.service..."

cat > /etc/systemd/system/skud-nfc.service << EOF
[Unit]
Description=СКУД NFC Service - Фоновый демон для обработки NFC карт
After=network.target

[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$VENV_DIR/bin"
Environment="PYTHONUNBUFFERED=1"
ExecStart=$VENV_DIR/bin/python3 $PROJECT_DIR/nfc_service.py --zone 1
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=skud-nfc

# Ограничения безопасности
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# Создание сервиса веб-сервера
log_info "Создание сервиса skud-web.service..."

cat > /etc/systemd/system/skud-web.service << EOF
[Unit]
Description=СКУД Web Server - Веб-интерфейс системы контроля доступа
After=network.target skud-nfc.service

[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$VENV_DIR/bin"
Environment="PYTHONUNBUFFERED=1"
ExecStart=$VENV_DIR/bin/python3 $PROJECT_DIR/app.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=skud-web

# Ограничения безопасности
NoNewPrivileges=true
PrivateTmp=true

# Порт (если нужно привилегированный)
# AmbientCapabilities=CAP_NET_BIND_SERVICE
# CapabilityBoundingSet=CAP_NET_BIND_SERVICE

[Install]
WantedBy=multi-user.target
EOF

# Перезагрузка systemd
log_info "Перезагрузка systemd..."
systemctl daemon-reload

# Включение сервисов
log_info "Включение сервисов..."
systemctl enable skud-nfc.service
systemctl enable skud-web.service

log_info "============================================================"
log_info "  Сервисы установлены!"
log_info "============================================================"
echo ""
echo "  Управление сервисами:"
echo ""
echo "  # Запуск"
echo "  sudo systemctl start skud-nfc"
echo "  sudo systemctl start skud-web"
echo ""
echo "  # Проверка статуса"
echo "  sudo systemctl status skud-nfc"
echo "  sudo systemctl status skud-web"
echo ""
echo "  # Просмотр логов"
echo "  sudo journalctl -u skud-nfc -f"
echo "  sudo journalctl -u skud-web -f"
echo ""
echo "  # Остановка"
echo "  sudo systemctl stop skud-nfc"
echo "  sudo systemctl stop skud-web"
echo ""
echo "  # Перезапуск"
echo "  sudo systemctl restart skud-nfc"
echo "  sudo systemctl restart skud-web"
echo ""
echo "  # Отключение автозапуска"
echo "  sudo systemctl disable skud-nfc"
echo "  sudo systemctl disable skud-web"
echo ""
echo "============================================================"
echo ""
log_info "Запуск сервисов..."

systemctl start skud-nfc.service
systemctl start skud-web.service

sleep 2

# Проверка статуса
echo ""
log_info "Статус сервисов:"
systemctl status skud-nfc.service --no-pager -l
echo ""
systemctl status skud-web.service --no-pager -l

echo ""
log_info "============================================================"
log_info "  Готово!"
log_info "============================================================"
echo ""
echo "  Веб-интерфейс доступен по адресу:"
echo "  http://localhost:5000"
echo "  или"
echo "  http://$(hostname -I | awk '{print $1}'):5000"
echo ""
echo "  Логи сервисов:"
echo "  sudo journalctl -u skud-nfc -f"
echo "  sudo journalctl -u skud-web -f"
echo "============================================================"
