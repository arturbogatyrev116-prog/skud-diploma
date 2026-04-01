#!/bin/bash
# Скрипт очистки избыточных файлов после оптимизации

echo "🗑️  Очистка избыточных файлов..."

# Удаление старых файлов
rm -fv install_rpi.sh
rm -fv install_rpi_simple.sh
rm -fv start_nfc_service.sh
rm -fv start_web_server.sh
rm -fv INSTALL_FIX.md
rm -fv NFC_CHANGES.md
rm -fv README_NFC.md
rm -fv README_PN532_ADAFRUIT.md
rm -fv QUICKSTART_NFC.md
rm -fv INSTALL_TROUBLESHOOTING.md
rm -fv output.log

# Перемещение в структурированные папки
echo ""
echo "📁 Создание структуры папок..."

mkdir -p core
mkdir -p nfc
mkdir -p tests
mkdir -p scripts

# Перемещение файлов ядра
echo ""
echo "🔄 Перемещение файлов ядра..."
mv -v app.py core/ 2>/dev/null || echo "app.py уже в core/"
mv -v auth_logic.py core/ 2>/dev/null || echo "auth_logic.py уже в core/"
mv -v database.py core/ 2>/dev/null || echo "database.py уже в core/"
mv -v config.py core/ 2>/dev/null || echo "config.py уже в core/"

# Перемещение NFC файлов
echo ""
echo "🔄 Перемещение NFC файлов..."
mv -v nfc_reader.py nfc/reader.py 2>/dev/null || echo "nfc_reader.py уже в nfc/"
mv -v nfc_service.py nfc/service.py 2>/dev/null || echo "nfc_service.py уже в nfc/"

# Перемещение тестов
echo ""
echo "🔄 Перемещение тестов..."
mv -v test_full.py tests/test_core.py 2>/dev/null || echo "test_full.py уже в tests/"

# Перемещение скриптов
echo ""
echo "🔄 Перемещение скриптов..."
mv -v install.sh scripts/ 2>/dev/null || echo "install.sh уже в scripts/"
mv -v install_systemd.sh scripts/ 2>/dev/null || echo "install_systemd.sh уже в scripts/"

echo ""
echo "✅ Очистка завершена!"
echo ""
echo "📁 Новая структура:"
echo "  core/      — ядро системы"
echo "  nfc/       — NFC модуль"
echo "  tests/     — тесты"
echo "  scripts/   — скрипты"
echo "  docs/      — документация"
echo ""
echo "📝 Не забудьте обновить импорты в файлах!"
