#!/bin/bash
# Скрипт запуска NFC сервиса СКУД
# Для использования: sudo ./start_nfc_service.sh [--zone N] [--auto-register] [--rank N]

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"

echo "============================================================"
echo "  Запуск NFC сервиса СКУД"
echo "============================================================"

# Проверка виртуального окружения
if [ ! -d "$VENV_DIR" ]; then
    echo "⚠️  Виртуальное окружение не найдено."
    echo "   Запустите: sudo ./install_rpi.sh"
    exit 1
fi

# Активация виртуального окружения
echo "📦 Активация виртуального окружения..."
source "$VENV_DIR/bin/activate"

# Проверка прав root
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  Для работы с NFC требуются права root."
    echo "   Запустите: sudo ./start_nfc_service.sh"
    exit 1
fi

# Запуск сервиса
echo "🚀 Запуск NFC сервиса..."
echo ""
echo "  Параметры: $@"
echo "  Нажмите Ctrl+C для остановки"
echo ""
echo "============================================================"

cd "$PROJECT_DIR"
python3 nfc_service.py "$@"
