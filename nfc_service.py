"""
NFC Service — фоновый демон для обработки NFC-карт
Интеграция с системой СКУД через WebSocket и REST API
"""
import os
import sys
import time
import json
import signal
import logging
import threading
import hashlib
import hmac
from typing import Optional, Callable
from datetime import datetime

# Добавляем текущую директорию в path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nfc_reader import NFCReader
from database import (
    get_user, get_user_current_zone, get_zones_info,
    get_user_history, create_pending_pass, log_access,
    check_block, increment_fail, reset_fail, add_user
)
from auth_logic import calculate_rank, is_history_valid, is_route_valid, is_context_valid
from config import (
    MAX_ATTEMPTS_RANK_HIGH, MAX_ATTEMPTS_RANK_MEDIUM,
    MAX_ATTEMPTS_RANK_LOW, BLOCK_DURATION_MINUTES
)

# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class NFCService:
    """
    Фоновый сервис для обработки NFC-карт
    
    Работает в режиме демона, опрашивает NFC-ридер
    и автоматически обрабатывает попытки доступа
    """
    
    def __init__(
        self, 
        zone_to: int = 1,
        auto_register: bool = False,
        default_rank: int = 4,
        callback: Optional[Callable] = None
    ):
        """
        Инициализация NFC сервиса
        
        Args:
            zone_to: Зона доступа по умолчанию (куда пытается пройти пользователь)
            auto_register: Автоматически регистрировать новые карты
            default_rank: Ранг для автоматически регистрируемых пользователей
            callback: Функция обратного вызова при событиях
        """
        self.zone_to = zone_to
        self.auto_register = auto_register
        self.default_rank = default_rank
        self.callback = callback
        
        self.reader = NFCReader()
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.last_uid: Optional[str] = None
        self.last_read_time: float = 0
        self.read_cooldown = 2.0  # Защита от повторных срабатываний
        
        # Статистика
        self.stats = {
            'total_reads': 0,
            'successful_access': 0,
            'denied_access': 0,
            'unknown_cards': 0,
            'start_time': None
        }
    
    def _log_event(self, event_type: str, data: dict):
        """Логирование события с отправкой callback"""
        timestamp = datetime.now().isoformat()
        event = {
            'timestamp': timestamp,
            'type': event_type,
            'data': data
        }
        
        logger.info(f"{event_type}: {json.dumps(data, ensure_ascii=False)}")
        
        if self.callback:
            self.callback(event)
    
    def _authenticate_user(
        self, 
        uid: str, 
        user: dict, 
        history: list,
        zones_info: dict
    ) -> tuple:
        """
        Аутентификация пользователя
        
        Returns:
            (success, message, combination)
        """
        user_rank = user['rank']
        
        # Определение количества попыток
        if user_rank >= 8:
            max_attempts = MAX_ATTEMPTS_RANK_HIGH
        elif user_rank >= 7:
            max_attempts = MAX_ATTEMPTS_RANK_MEDIUM
        else:
            max_attempts = MAX_ATTEMPTS_RANK_LOW
        
        required_rank = zones_info[self.zone_to]['required_rank']
        
        # Попытка аутентификации
        for attempt in range(max_attempts):
            nonce = os.urandom(16)
            history_bytes = json.dumps(history).encode()
            T = hmac.new(
                user['secret_key'].encode(), 
                nonce + history_bytes, 
                hashlib.sha256
            ).digest()
            combination = [(b % 13) + 1 for b in T[:5]]
            actual_rank = calculate_rank(combination)
            
            if actual_rank == user_rank:
                # Проверка прав доступа
                if user_rank >= required_rank:
                    return True, "Доступ разрешён", combination
                else:
                    return False, f"Недостаточно прав: {user_rank} < {required_rank}", None
        
        return False, "Аутентификация не удалась", None
    
    def _process_card(self, uid: str):
        """Обработка обнаруженной карты"""
        # Проверка cooldown
        current_time = time.time()
        if current_time - self.last_read_time < self.read_cooldown:
            logger.debug(f"Cooldown активен, пропускаем {uid}")
            return
        
        self.last_read_time = current_time
        self.last_uid = uid
        self.stats['total_reads'] += 1
        
        self._log_event('card_detected', {'uid': uid})
        
        # Проверка блокировки
        is_blocked, fail_count = check_block(uid)
        if is_blocked:
            self._log_event('access_denied', {
                'uid': uid,
                'reason': 'blocked',
                'fail_count': fail_count
            })
            print(f"❌ Карта {uid}: ЗАБЛОКИРОВАНА ({fail_count} неудачных попыток)")
            return
        
        # Получение информации о пользователе
        user = get_user(uid)
        
        if not user:
            self.stats['unknown_cards'] += 1
            
            if self.auto_register:
                # Автоматическая регистрация
                secret_key = os.urandom(32)
                add_user(uid, self.default_rank, secret_key, current_zone=0)
                user = get_user(uid)
                self._log_event('user_registered', {
                    'uid': uid,
                    'rank': self.default_rank
                })
                print(f"✅ Зарегистрирована новая карта: {uid} (ранг {self.default_rank})")
            else:
                self._log_event('unknown_card', {'uid': uid})
                print(f"❓ Неизвестная карта: {uid}")
                return
        
        # Получение текущей зоны и истории
        current_zone = get_user_current_zone(uid)
        history = get_user_history(uid, limit=5)
        
        if not history:
            history = [current_zone]
        
        zones_info = get_zones_info()
        
        # Проверка существования зоны
        if self.zone_to not in zones_info:
            self._log_event('access_denied', {
                'uid': uid,
                'reason': f'zone {self.zone_to} not found'
            })
            print(f"❌ Зона {self.zone_to} не существует")
            return
        
        # Валидация истории
        history_valid, history_msg = is_history_valid(history, zones_info)
        if not history_valid:
            log_access(uid, current_zone, self.zone_to, False, history_msg)
            self._log_event('access_denied', {
                'uid': uid,
                'reason': history_msg
            })
            print(f"❌ {uid}: {history_msg}")
            return
        
        # Контекстная проверка
        context_valid, context_msg = is_context_valid(history, self.zone_to, zones_info)
        if not context_valid:
            log_access(uid, current_zone, self.zone_to, False, context_msg)
            self._log_event('access_denied', {
                'uid': uid,
                'reason': context_msg
            })
            print(f"❌ {uid}: {context_msg}")
            return
        
        # Проверка маршрута
        route_valid, route_msg = is_route_valid(history, self.zone_to, zones_info)
        if not route_valid:
            log_access(uid, current_zone, self.zone_to, False, route_msg)
            self._log_event('access_denied', {
                'uid': uid,
                'reason': route_msg
            })
            print(f"❌ {uid}: {route_msg}")
            return
        
        # Аутентификация
        auth_success, auth_msg, combination = self._authenticate_user(
            uid, user, history, zones_info
        )
        
        if not auth_success:
            # Увеличение счётчика неудачных попыток
            is_blocked, blocked_until = increment_fail(uid)
            
            self.stats['denied_access'] += 1
            self._log_event('access_denied', {
                'uid': uid,
                'reason': auth_msg,
                'blocked': is_blocked
            })
            
            if is_blocked:
                print(f"🔒 {uid}: ЗАБЛОКИРОВАН на {BLOCK_DURATION_MINUTES} мин")
            else:
                _, current_fails = check_block(uid)
                print(f"❌ {uid}: {auth_msg} ({current_fails}/3)")
            return
        
        # Успех!
        create_pending_pass(uid, current_zone, self.zone_to)
        reset_fail(uid)
        
        self.stats['successful_access'] += 1
        self._log_event('access_granted', {
            'uid': uid,
            'zone_from': current_zone,
            'zone_to': self.zone_to,
            'combination': combination
        })
        
        zone_name = zones_info[self.zone_to]['name']
        print(f"✅ {uid}: ДОСТУП РАЗРЕШЁН в зону '{zone_name}'")
        print(f"   Комбинация: {combination}")
        
        # Автоматическое подтверждение прохода через 2 секунды
        # (для демонстрации, в продакшене лучше требовать подтверждения)
        # confirm_pass(uid)
    
    def _run_loop(self):
        """Основной цикл сервиса (в отдельном потоке)"""
        logger.info("NFC Service: запуск цикла опроса")
        
        while self.running:
            try:
                uid = self.reader.read_card_uid(timeout=500)
                if uid:
                    self._process_card(uid)
            except Exception as e:
                logger.error(f"Ошибка в цикле опроса: {e}")
                time.sleep(1)
            
            time.sleep(0.1)
        
        logger.info("NFC Service: цикл опроса остановлен")
    
    def start(self, blocking: bool = True):
        """
        Запуск сервиса
        
        Args:
            blocking: Если True, блокирует выполнение (работает в главном потоке)
                     Если False, запускает фоновую потоку
        """
        logger.info("NFC Service: инициализация...")
        
        if not self.reader.init():
            logger.error("NFC Service: ошибка инициализации ридера")
            return False
        
        self.running = True
        self.stats['start_time'] = datetime.now().isoformat()
        
        # Обработка сигналов
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        print("\n" + "=" * 60)
        print("🔓 NFC SERVICE ЗАПУЩЕН")
        print("=" * 60)
        print(f"  Зона доступа: {self.zone_to}")
        print(f"  Авто-регистрация: {'включена' if self.auto_register else 'выключена'}")
        print(f"  Ранг по умолчанию: {self.default_rank}")
        print("=" * 60)
        print("\nПрикладывайте карты для проверки доступа...\n")
        
        self._log_event('service_started', {
            'zone_to': self.zone_to,
            'auto_register': self.auto_register,
            'default_rank': self.default_rank
        })
        
        if blocking:
            self._run_loop()
        else:
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
        
        return True
    
    def stop(self):
        """Остановка сервиса"""
        logger.info("NFC Service: остановка...")
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=5)
        
        self.reader.close()
        
        self._log_event('service_stopped', self.stats)
        
        print("\n" + "=" * 60)
        print("📊 СТАТИСТИКА NFC SERVICE")
        print("=" * 60)
        print(f"  Всего прочтений: {self.stats['total_reads']}")
        print(f"  Успешный доступ: {self.stats['successful_access']}")
        print(f"  Отказано: {self.stats['denied_access']}")
        print(f"  Неизвестные карты: {self.stats['unknown_cards']}")
        print("=" * 60)
    
    def _signal_handler(self, signum, frame):
        """Обработчик сигналов завершения"""
        logger.info(f"Получен сигнал {signum}, завершение работы...")
        self.stop()
        sys.exit(0)
    
    def get_stats(self) -> dict:
        """Получить статистику сервиса"""
        return self.stats.copy()


def run_service(
    zone_to: int = 1,
    auto_register: bool = False,
    default_rank: int = 4
):
    """
    Запустить NFC сервис
    
    Args:
        zone_to: Зона для проверки доступа
        auto_register: Регистрировать ли новые карты
        default_rank: Ранг для новых карт
    """
    service = NFCService(
        zone_to=zone_to,
        auto_register=auto_register,
        default_rank=default_rank
    )
    service.start(blocking=True)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='NFC Service для системы СКУД',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Примеры использования:
  %(prog)s --zone 1                    # Проверка доступа в Офис (зона 1)
  %(prog)s --zone 2 --auto-register    # Серверная с авто-регистрацией
  %(prog)s --zone 0 --rank 3           # Вход для посетителей
        '''
    )
    
    parser.add_argument(
        '--zone', '-z',
        type=int,
        default=1,
        help='Зона доступа (по умолчанию: 1 = Офис)'
    )
    
    parser.add_argument(
        '--auto-register', '-a',
        action='store_true',
        help='Автоматически регистрировать новые карты'
    )
    
    parser.add_argument(
        '--rank', '-r',
        type=int,
        default=4,
        choices=range(3, 10),
        metavar='3-9',
        help='Ранг для авто-регистрации (по умолчанию: 4)'
    )
    
    parser.add_argument(
        '--debug', '-d',
        action='store_true',
        help='Режим отладки'
    )
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    run_service(
        zone_to=args.zone,
        auto_register=args.auto_register,
        default_rank=args.rank
    )
