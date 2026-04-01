# 🔧 Решение проблем

## PN532 не определяется

### I2C
```bash
sudo i2cdetect -y 1
# Должно показать: 24 на позиции 0x24
```

### SPI
```bash
ls /dev/spi*
# Должно быть: /dev/spidev0.0
```

### Решение
```bash
sudo usermod -a -G spi pi
sudo usermod -a -G i2c pi
sudo reboot
```

## Ошибка: "No module named 'adafruit_pn532'"

```bash
source venv/bin/activate
pip install adafruit-circuitpython-pn532
```

## Карта не читается

1. Проверьте расстояние (карта вплотную к антенне)
2. Попробуйте другую карту (NTAG213/215/216)
3. Уберите металлические предметы

## Логи

```bash
sudo journalctl -u skud-nfc -f
sudo journalctl -u skud-web -f
```
