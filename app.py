"""
Веб-сервер системы СКУД
Flask приложение для управления доступом и мониторинга событий
"""
import os
import json
import time
import datetime
import logging
from io import BytesIO
from typing import Optional
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify
from flask_wtf.csrf import CSRFProtect
from cryptography.fernet import Fernet, InvalidToken
from config import (
    SECRET_KEY, NFC_TOKEN_KEY,
    MAX_ATTEMPTS_RANK_HIGH, MAX_ATTEMPTS_RANK_MEDIUM,
    MAX_ATTEMPTS_RANK_LOW, BLOCK_DURATION_MINUTES,
    MIN_RANK, MAX_RANK,
    NFC_INTERFACE, NFC_RST_PIN, NFC_IRQ_PIN, NFC_SPI_CE, NFC_UART_PORT
)
from database import (
    init_db, add_user, get_user, get_user_by_nfc_uid, log_access, get_zones_info,
    check_block, increment_fail, reset_fail, get_block_until,
    create_pending_pass, confirm_pass, cleanup_expired_passes,
    get_user_current_zone, get_user_history, get_all_users,
    get_recent_logs, delete_user, update_user,
    get_users_with_zones, get_zone_users
)
from auth_logic import calculate_rank, is_history_valid, is_route_valid, is_context_valid, authenticate_user

# Импорт NFC модуля (опционально)
try:
    from nfc_reader import NFCReader, ADAFRUIT_AVAILABLE as NFC_HARDWARE_AVAILABLE
    NFC_AVAILABLE = True
except ImportError:
    NFC_AVAILABLE = False
    NFC_HARDWARE_AVAILABLE = False
    NFCReader = None

# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def _plural_minutes(n: int) -> str:
    if 11 <= n % 100 <= 19:
        return f"{n} минут"
    rem = n % 10
    if rem == 1:
        return f"{n} минуту"
    if rem in (2, 3, 4):
        return f"{n} минуты"
    return f"{n} минут"


app = Flask(__name__)
app.secret_key = SECRET_KEY
csrf = CSRFProtect(app)

# Доверяем заголовкам X-Forwarded-Proto и X-Forwarded-Host от ngrok/Caddy
# Без этого url_for(_external=True) и request.host_url возвращают http:// вместо https://
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# NFC-токены: шифрование Fernet (симметричный AES-128-CBC + HMAC-SHA256)
_fernet: Optional[Fernet] = Fernet(NFC_TOKEN_KEY.encode()) if NFC_TOKEN_KEY and NFC_TOKEN_KEY != 'generate_nfc_key_placeholder' else None


def _make_nfc_token(uid: str, rank: int, zone: int) -> Optional[str]:
    """Шифрует данные карты в Fernet-токен для записи на NFC-чип."""
    if not _fernet:
        return None
    payload = json.dumps({"uid": uid, "rank": rank, "zone": zone, "iat": int(time.time())})
    return _fernet.encrypt(payload.encode()).decode()


def _decode_nfc_token(token_str: str) -> Optional[dict]:
    """Расшифровывает Fernet-токен. Возвращает None если токен недействителен."""
    if not _fernet or not token_str:
        return None
    try:
        raw = _fernet.decrypt(token_str.encode())
        return json.loads(raw)
    except (InvalidToken, Exception):
        return None


# Инициализация БД при старте
init_db()

# Глобальный NFC reader (ленивая инициализация)
_nfc_reader = None


def get_nfc_reader() -> Optional['NFCReader']:
    """Получить NFC reader (ленивая инициализация)"""
    global _nfc_reader
    if not NFC_AVAILABLE:
        return None
    if _nfc_reader is None:
        _nfc_reader = NFCReader(
            interface=NFC_INTERFACE,
            rst_pin=NFC_RST_PIN,
            irq_pin=NFC_IRQ_PIN,
            spi_ce=NFC_SPI_CE,
            uart_port=NFC_UART_PORT,
        )
        _nfc_reader.init()
    return _nfc_reader


@app.route('/')
def landing():
    """Главная страница — выбор устройства (телефон / компьютер)"""
    return render_template('landing.html')


@app.route('/desktop')
def index():
    """Десктопный интерфейс — эмуляция прохода (прежняя главная)"""
    cleanup_expired_passes()
    users_list = get_all_users()
    return render_template('index.html', users=users_list)


@app.route('/users')
def users():
    """Страница управления пользователями"""
    users_list = get_all_users()
    return render_template('users.html', users=users_list)


@app.route('/logs')
def logs():
    """Страница журнала событий"""
    logs_list = get_recent_logs(100)
    return render_template('logs.html', logs=logs_list)


@app.route('/dashboard')
def dashboard():
    """Страница схемы офиса"""
    return render_template('dashboard.html')


@app.route('/terminal')
def terminal():
    """Виртуальный NFC-терминал (программная эмуляция считывателя PN532)"""
    users_list = get_all_users()
    zones_info = get_zones_info()
    return render_template('terminal.html', users=users_list, zones=zones_info)


@app.route('/mobile')
def mobile_root():
    """Корень мобильного интерфейса — редирект на сканер"""
    return redirect(url_for('mobile_scan'))


@app.route('/mobile/scan')
def mobile_scan():
    """Мобильный сканер — Web NFC через Android Chrome + fallback селектор"""
    users_list = get_all_users()
    zones_info = get_zones_info()
    return render_template('m_scan.html', users=users_list, zones=zones_info)


@app.route('/mobile/register')
def mobile_register():
    """Мобильная регистрация новой карты"""
    zones_info = get_zones_info()
    return render_template('m_register.html', zones=zones_info)


@app.route('/mobile/users')
def mobile_users():
    """Мобильный список пользователей"""
    users_list = get_users_with_zones()
    return render_template('m_users.html', users=users_list)


@app.route('/mobile/logs')
def mobile_logs():
    """Мобильный журнал событий"""
    logs_list = get_recent_logs(100)
    zones_info = get_zones_info()
    return render_template('m_logs.html', logs=logs_list, zones=zones_info)


# Кэш сгенерированных QR-кодов по URL (ngrok URL стабилен в рамках сессии)
_qr_cache: dict = {}


@app.route('/qr/mobile')
def qr_mobile():
    """PNG QR-кода со ссылкой на /mobile/scan (для удобного открытия на телефоне)"""
    import qrcode
    # Берём host из текущего запроса — при открытии через ngrok это будет ngrok-URL,
    # при открытии с localhost — localhost. QR всегда указывает на тот же хост.
    target_url = request.host_url.rstrip('/') + '/mobile/scan'
    cache_key = request.host
    if cache_key not in _qr_cache:
        img = qrcode.make(target_url, box_size=10, border=2)
        buf = BytesIO()
        img.save(buf, format='PNG')
        _qr_cache[cache_key] = buf.getvalue()
    return send_file(BytesIO(_qr_cache[cache_key]), mimetype='image/png')


@app.route('/manifest.json')
@csrf.exempt
def manifest():
    """PWA-манифест для 'Добавить на главный экран' на Android"""
    return jsonify({
        "name": "СКУД Сканер",
        "short_name": "СКУД",
        "start_url": "/mobile/scan",
        "display": "standalone",
        "orientation": "portrait",
        "theme_color": "#1a252f",
        "background_color": "#1a252f",
        "icons": []
    })


@app.route('/add_user', methods=['POST'])
def add_user_route():
    """Добавление нового пользователя"""
    uid = request.form['uid']
    rank = int(request.form['rank'])
    name = request.form.get('name', 'User')
    secret_key = os.urandom(32)
    
    try:
        add_user(uid, rank, secret_key)
        flash(f"Пользователь {uid} ({name}) добавлен с рангом {rank}!", "success")
        logger.info(f"Добавлен пользователь: {uid}, ранг {rank}")
    except Exception as e:
        flash(f"Ошибка добавления пользователя: {e}", "error")
        logger.error(f"Ошибка добавления пользователя {uid}: {e}")
    
    return redirect(url_for('users'))


@app.route('/simulate_access', methods=['POST'])
def simulate_access():
    """Эмуляция проверки доступа"""
    uid = request.form['uid']
    zone_to = int(request.form['zone_to'])
    
    # Проверка блокировки
    is_blocked, fail_count = check_block(uid)
    if is_blocked:
        blocked_until = get_block_until(uid)
        if blocked_until:
            remaining = max(0, int((blocked_until - datetime.datetime.now()).total_seconds()))
            flash(f"Доступ заблокирован. Осталось {remaining} секунд.", "error")
        else:
            flash("Доступ заблокирован.", "error")
        logger.warning(f"Попытка доступа заблокированного пользователя: {uid}")
        return redirect(url_for('index'))
    
    # Проверка существования пользователя
    user = get_user(uid)
    if not user:
        flash("Пользователь не найден!", "error")
        logger.warning(f"Попытка доступа несуществующего пользователя: {uid}")
        return redirect(url_for('index'))
    
    # Проверка существования зоны
    zones_info = get_zones_info()
    if zone_to not in zones_info:
        flash(f"Зона {zone_to} не существует!", "error")
        logger.warning(f"Попытка доступа в несуществующую зону {zone_to} пользователем {uid}")
        return redirect(url_for('index'))
    
    # Получаем текущую зону и историю перемещений
    current_zone = get_user_current_zone(uid)
    history = get_user_history(uid, limit=5)
    
    # Если истории нет, используем текущую зону
    if not history:
        history = [current_zone]
    
    # Валидация истории (существование зон)
    history_valid, history_msg = is_history_valid(history, zones_info)
    if not history_valid:
        log_access(uid, current_zone, zone_to, False, f"Некорректная история: {history_msg}")
        flash(f"{history_msg}", "error")
        logger.warning(f"Некорректная история для {uid}: {history_msg}")
        return redirect(url_for('index'))
    
    # Контекстная проверка
    context_valid, context_msg = is_context_valid(history, zone_to, zones_info)
    if not context_valid:
        log_access(uid, current_zone, zone_to, False, context_msg)
        flash(f"{context_msg}", "error")
        logger.warning(f"Нарушение контекста для {uid}: {context_msg}")
        return redirect(url_for('index'))
    
    # Проверка маршрута
    route_valid, route_msg = is_route_valid(history, zone_to, zones_info)
    if not route_valid:
        log_access(uid, current_zone, zone_to, False, route_msg)
        flash(f"{route_msg}", "error")
        logger.warning(f"Нарушение маршрута для {uid}: {route_msg}")
        return redirect(url_for('index'))
    
    user_rank = user['rank']
    if user_rank >= 8:
        max_attempts = MAX_ATTEMPTS_RANK_HIGH
    elif user_rank >= 7:
        max_attempts = MAX_ATTEMPTS_RANK_MEDIUM
    else:
        max_attempts = MAX_ATTEMPTS_RANK_LOW

    required_rank = zones_info[zone_to]['required_rank']
    auth_success, _ = authenticate_user(user['secret_key'], user_rank, history, max_attempts)

    if not auth_success:
        is_blocked, blocked_until = increment_fail(uid)
        if is_blocked:
            flash(f"Доступ заблокирован на {_plural_minutes(BLOCK_DURATION_MINUTES)} из-за 3 неудачных попыток", "error")
            logger.warning(f"Пользователь {uid} заблокирован после 3 неудачных попыток")
        else:
            _, current_fails = check_block(uid)
            flash(f"Неудачная попытка аутентификации ({current_fails}/{3})", "error")
            logger.info(f"Неудачная аутентификация для {uid}: попытка {current_fails}/3")
        return redirect(url_for('index'))
    
    # Проверка прав доступа
    if user_rank >= required_rank:
        # Создаём временную сессию прохода
        create_pending_pass(uid, current_zone, zone_to)
        session['current_uid'] = uid
        flash(f"Дверь открыта на 10 секунд. Подтвердите проход!", "success")
        logger.info(f"Доступ разрешён: {uid} ({user_rank}) → зона {zone_to} (требуется {required_rank})")
    else:
        reason = f"Недостаточно прав: ранг {user_rank} < {required_rank}"
        log_access(uid, current_zone, zone_to, False, reason)
        flash(f"{reason}", "error")
        logger.info(f"Отказано в доступе: {uid} ({user_rank}) < {required_rank}")
    
    return redirect(url_for('index'))


@app.route('/confirm_pass/<uid>', methods=['POST'])
def confirm_pass_route(uid):
    """Подтверждение прохода"""
    try:
        confirm_pass(uid)
        flash("Проход подтверждён", "success")
        # Очищаем сессию
        if 'current_uid' in session:
            del session['current_uid']
    except Exception as e:
        flash(f"Ошибка подтверждения: {str(e)}", "error")
        logger.error(f"Ошибка подтверждения прохода для {uid}: {e}")

    return redirect(url_for('index'))


@app.route('/delete_user/<uid>', methods=['POST'])
def delete_user_route(uid):
    """Удаление пользователя"""
    try:
        if delete_user(uid):
            flash(f"Пользователь {uid} удалён", "success")
            logger.info(f"Пользователь {uid} удалён через веб-интерфейс")
        else:
            flash(f"Пользователь {uid} не найден", "error")
            logger.warning(f"Попытка удаления несуществующего пользователя {uid}")
    except Exception as e:
        flash(f"Ошибка удаления: {str(e)}", "error")
        logger.error(f"Ошибка удаления пользователя {uid}: {e}")
    
    return redirect(url_for('users'))


@app.route('/edit_user/<uid>', methods=['GET', 'POST'])
def edit_user_route(uid):
    """Редактирование пользователя"""
    user = get_user(uid)
    
    if not user:
        flash(f"Пользователь {uid} не найден", "error")
        return redirect(url_for('users'))
    
    if request.method == 'POST':
        try:
            new_rank = int(request.form.get('rank', user['rank']))
            new_zone = int(request.form.get('current_zone', user['current_zone']))
            
            if update_user(uid, rank=new_rank, current_zone=new_zone):
                flash(f"Пользователь {uid} обновлён", "success")
                logger.info(f"Пользователь {uid} обновлён: ранг={new_rank}, зона={new_zone}")
            else:
                flash("Ошибка обновления пользователя", "error")
            
            return redirect(url_for('users'))
        except Exception as e:
            flash(f"Ошибка обновления: {str(e)}", "error")
            logger.error(f"Ошибка обновления пользователя {uid}: {e}")
    
    # GET запрос - показываем форму редактирования
    zones_info = get_zones_info()
    return render_template('edit_user.html', user=user, zones=zones_info)


@app.route('/api/users')
@csrf.exempt
def api_users():
    """API: Получить всех пользователей с их зонами"""
    users = get_users_with_zones()
    return {
        'users': [
            {
                'uid': u['uid'],
                'rank': u['rank'],
                'current_zone': u['current_zone'],
                'zone_name': u['zone_name'] or 'Неизвестно',
                'created_at': u['created_at']
            }
            for u in users
        ]
    }


@app.route('/api/zones')
@csrf.exempt
def api_zones():
    """API: Получить все зоны"""
    zones = get_zones_info()
    return {
        'zones': [
            {
                'id': zone_id,
                'name': zone_data['name'],
                'is_exit': zone_data['is_exit'],
                'required_rank': zone_data['required_rank']
            }
            for zone_id, zone_data in zones.items()
        ]
    }


@app.route('/api/status')
@csrf.exempt
def api_status():
    """API: Получить статус системы (пользователи по зонам)"""
    zones = get_zones_info()
    users_by_zone = {}

    for zone_id in zones.keys():
        zone_users = get_zone_users(zone_id)
        users_by_zone[str(zone_id)] = [
            {'uid': u['uid'], 'rank': u['rank']}
            for u in zone_users
        ]

    return {
        'zones': zones,
        'users_by_zone': users_by_zone,
        'total_users': sum(len(v) for v in users_by_zone.values())
    }


@app.route('/api/nfc/status')
@csrf.exempt
def api_nfc_status():
    """API: Проверить доступность NFC-ридера"""
    emulation = NFC_AVAILABLE and not NFC_HARDWARE_AVAILABLE
    return {
        'available': NFC_AVAILABLE,
        'initialized': _nfc_reader is not None and _nfc_reader.initialized if NFC_AVAILABLE else False,
        'emulation': emulation
    }


@app.route('/api/nfc/read', methods=['POST'])
@csrf.exempt
def api_nfc_read():
    """API: Считать UID карты (однократно)"""
    if not NFC_AVAILABLE:
        return {'error': 'NFC модуль недоступен. Установите библиотеку pn532.'}, 503
    
    reader = get_nfc_reader()
    if not reader or not reader.initialized:
        return {'error': 'NFC ридер не инициализирован'}, 503
    
    timeout = request.json.get('timeout', 1000) if request.json else 1000
    uid = reader.read_card_uid(timeout=timeout)
    
    if uid:
        # Проверяем, существует ли пользователь
        user = get_user(uid)
        return {
            'uid': uid,
            'user_exists': user is not None,
            'user': {
                'uid': user['uid'],
                'rank': user['rank'],
                'current_zone': user['current_zone'],
                'zone_name': get_zones_info().get(user['current_zone'], {}).get('name', 'Неизвестно')
            } if user else None
        }
    else:
        return {'uid': None, 'message': 'Карта не обнаружена'}


@app.route('/api/nfc/poll', methods=['GET', 'POST'])
@csrf.exempt
def api_nfc_poll():
    """
    API: Опросить NFC-ридер и обработать доступ
    
    Возвращает результат попытки доступа:
    - success: True/False
    - uid: UID карты
    - message: Сообщение для пользователя
    - action: 'granted' | 'denied' | 'blocked' | 'unknown'
    """
    if not NFC_AVAILABLE:
        return {'error': 'NFC модуль недоступен'}, 503
    
    reader = get_nfc_reader()
    if not reader or not reader.initialized:
        return {'error': 'NFC ридер не инициализирован'}, 503
    
    # Читаем UID
    uid = reader.read_card_uid(timeout=500)
    
    if not uid:
        return {'success': False, 'action': 'no_card', 'message': 'Карта не обнаружена'}
    
    # Проверка блокировки
    is_blocked, fail_count = check_block(uid)
    if is_blocked:
        return {
            'success': False,
            'action': 'blocked',
            'uid': uid,
            'message': f'Доступ заблокирован ({fail_count} неудачных попыток)'
        }
    
    # Проверка существования пользователя
    user = get_user(uid)
    if not user:
        return {
            'success': False,
            'action': 'unknown',
            'uid': uid,
            'message': 'Неизвестная карта. Зарегистрируйте пользователя.'
        }
    
    # Получаем зону назначения из запроса или по умолчанию
    zone_to = request.json.get('zone_to', 1) if request.json else 1
    zones_info = get_zones_info()
    
    if zone_to not in zones_info:
        return {'success': False, 'action': 'error', 'message': f'Зона {zone_to} не существует'}
    
    # Получаем текущую зону и историю
    current_zone = get_user_current_zone(uid)
    history = get_user_history(uid, limit=5)
    if not history:
        history = [current_zone]
    
    # Валидация истории
    history_valid, history_msg = is_history_valid(history, zones_info)
    if not history_valid:
        log_access(uid, current_zone, zone_to, False, history_msg)
        return {'success': False, 'action': 'denied', 'uid': uid, 'message': history_msg}
    
    # Контекстная проверка
    context_valid, context_msg = is_context_valid(history, zone_to, zones_info)
    if not context_valid:
        log_access(uid, current_zone, zone_to, False, context_msg)
        return {'success': False, 'action': 'denied', 'uid': uid, 'message': context_msg}
    
    # Проверка маршрута
    route_valid, route_msg = is_route_valid(history, zone_to, zones_info)
    if not route_valid:
        log_access(uid, current_zone, zone_to, False, route_msg)
        return {'success': False, 'action': 'denied', 'uid': uid, 'message': route_msg}
    
    # Аутентификация
    user_rank = user['rank']
    if user_rank >= 8:
        max_attempts = MAX_ATTEMPTS_RANK_HIGH
    elif user_rank >= 7:
        max_attempts = MAX_ATTEMPTS_RANK_MEDIUM
    else:
        max_attempts = MAX_ATTEMPTS_RANK_LOW
    
    required_rank = zones_info[zone_to]['required_rank']
    auth_success, _ = authenticate_user(user['secret_key'], user_rank, history, max_attempts)

    if not auth_success:
        is_blocked, _ = increment_fail(uid)
        msg = 'Доступ заблокирован' if is_blocked else f'Неудачная попытка ({check_block(uid)[1]}/3)'
        return {
            'success': False,
            'action': 'denied' if not is_blocked else 'blocked',
            'uid': uid,
            'message': msg
        }
    
    # Проверка прав доступа
    if user_rank >= required_rank:
        create_pending_pass(uid, current_zone, zone_to)
        zone_name = zones_info[zone_to]['name']
        return {
            'success': True,
            'action': 'granted',
            'uid': uid,
            'message': f'Доступ разрешён в зону "{zone_name}"',
            'zone_from': current_zone,
            'zone_to': zone_to,
            'zone_name': zone_name
        }
    else:
        log_access(uid, current_zone, zone_to, False, f'Недостаточно прав: {user_rank} < {required_rank}')
        return {
            'success': False,
            'action': 'denied',
            'uid': uid,
            'message': f'Недостаточно прав: ранг {user_rank} < {required_rank}'
        }


@app.route('/api/terminal/scan', methods=['POST'])
@csrf.exempt
def api_terminal_scan():
    """
    API: Виртуальное сканирование карты (без физического PN532)

    Принимает UID карты и зону назначения, выполняет тот же путь
    аутентификации, что и физический считыватель.
    """
    data = request.json or {}
    uid = data.get('uid', '').strip()
    token_str = data.get('token', '').strip()
    zone_to = data.get('zone_to')

    # Если передан зашифрованный NFC-токен — расшифровать и взять uid из него
    if token_str:
        payload = _decode_nfc_token(token_str)
        if payload is None:
            return {'success': False, 'action': 'error', 'message': 'Недействительный NFC-токен'}, 400
        uid = payload.get('uid', uid)

    if not uid:
        return {'success': False, 'action': 'error', 'message': 'UID не указан'}, 400

    if zone_to is None:
        return {'success': False, 'action': 'error', 'message': 'Зона не указана'}, 400

    try:
        zone_to = int(zone_to)
    except (TypeError, ValueError):
        return {'success': False, 'action': 'error', 'message': 'Некорректная зона'}, 400

    # Проверка блокировки
    is_blocked, fail_count = check_block(uid)
    if is_blocked:
        return {
            'success': False,
            'action': 'blocked',
            'uid': uid,
            'message': f'Карта заблокирована ({fail_count} неудачных попыток)'
        }

    # Проверка существования пользователя (с fallback-нормализацией для NFC-чипов)
    user = get_user(uid)
    if not user:
        normalized_uid, user = get_user_by_nfc_uid(uid)
        if user:
            uid = normalized_uid
    if not user:
        return {
            'success': False,
            'action': 'unknown',
            'uid': uid,
            'message': 'Карта не зарегистрирована в системе'
        }

    # Проверка существования зоны
    zones_info = get_zones_info()
    if zone_to not in zones_info:
        return {
            'success': False,
            'action': 'error',
            'uid': uid,
            'message': f'Зона {zone_to} не существует'
        }

    # Получение текущей зоны и истории
    current_zone = get_user_current_zone(uid)
    history = get_user_history(uid, limit=5)
    if not history:
        history = [current_zone]

    # Валидация истории
    history_valid, history_msg = is_history_valid(history, zones_info)
    if not history_valid:
        log_access(uid, current_zone, zone_to, False, history_msg)
        return {'success': False, 'action': 'denied', 'uid': uid, 'message': history_msg}

    # Контекстная проверка
    context_valid, context_msg = is_context_valid(history, zone_to, zones_info)
    if not context_valid:
        log_access(uid, current_zone, zone_to, False, context_msg)
        return {'success': False, 'action': 'denied', 'uid': uid, 'message': context_msg}

    # Проверка маршрута
    route_valid, route_msg = is_route_valid(history, zone_to, zones_info)
    if not route_valid:
        log_access(uid, current_zone, zone_to, False, route_msg)
        return {'success': False, 'action': 'denied', 'uid': uid, 'message': route_msg}

    # Аутентификация
    user_rank = user['rank']
    if user_rank >= 8:
        max_attempts = MAX_ATTEMPTS_RANK_HIGH
    elif user_rank >= 7:
        max_attempts = MAX_ATTEMPTS_RANK_MEDIUM
    else:
        max_attempts = MAX_ATTEMPTS_RANK_LOW

    required_rank = zones_info[zone_to]['required_rank']
    auth_success, combination = authenticate_user(user['secret_key'], user_rank, history, max_attempts)

    if not auth_success:
        was_blocked, _ = increment_fail(uid)
        _, current_fails = check_block(uid)
        log_access(uid, current_zone, zone_to, False, 'Аутентификация не удалась')
        return {
            'success': False,
            'action': 'blocked' if was_blocked else 'denied',
            'uid': uid,
            'message': (
                f'Карта заблокирована на {BLOCK_DURATION_MINUTES} мин'
                if was_blocked else
                f'Аутентификация не удалась ({current_fails}/3)'
            )
        }

    # Проверка прав доступа
    if user_rank < required_rank:
        log_access(uid, current_zone, zone_to, False, f'Недостаточно прав: {user_rank} < {required_rank}')
        return {
            'success': False,
            'action': 'denied',
            'uid': uid,
            'message': f'Недостаточно прав: ранг {user_rank} < требуется {required_rank}'
        }

    # Успех
    create_pending_pass(uid, current_zone, zone_to)
    reset_fail(uid)

    return {
        'success': True,
        'action': 'granted',
        'uid': uid,
        'user_rank': user_rank,
        'zone_from': current_zone,
        'zone_from_name': zones_info.get(current_zone, {}).get('name', f'Зона {current_zone}'),
        'zone_to': zone_to,
        'zone_to_name': zones_info[zone_to]['name'],
        'combination': combination,
        'message': f'Доступ разрешён в зону "{zones_info[zone_to]["name"]}"'
    }


@app.route('/api/mobile/register', methods=['POST'])
@csrf.exempt
def api_mobile_register():
    """
    API: Регистрация новой карты с мобильного устройства.

    Принимает {uid, rank, zone?}, создаёт пользователя в БД.
    UID нормализуется (без двоеточий, upper) для единообразия.
    """
    data = request.json or {}
    raw_uid = (data.get('uid') or '').strip()
    rank = data.get('rank')
    zone = data.get('zone', 0)

    if not raw_uid:
        return {'success': False, 'message': 'UID не указан'}, 400

    # Нормализация UID — убрать разделители, привести к верхнему регистру
    normalized = raw_uid.replace(':', '').replace('-', '').replace(' ', '').upper()
    if not normalized:
        return {'success': False, 'message': 'Некорректный UID'}, 400

    try:
        rank = int(rank)
    except (TypeError, ValueError):
        return {'success': False, 'message': 'Ранг должен быть числом'}, 400

    if not (MIN_RANK <= rank <= MAX_RANK):
        return {'success': False, 'message': f'Ранг должен быть {MIN_RANK}–{MAX_RANK}'}, 400

    try:
        zone = int(zone)
    except (TypeError, ValueError):
        return {'success': False, 'message': 'Некорректная зона'}, 400

    zones_info = get_zones_info()
    if zone not in zones_info:
        return {'success': False, 'message': f'Зона {zone} не существует'}, 400

    # Проверка: карта уже зарегистрирована?
    existing = get_user(normalized)
    if existing:
        return {
            'success': False,
            'message': f'Карта {normalized} уже зарегистрирована (ранг {existing["rank"]})'
        }, 409

    secret_key = os.urandom(32)
    try:
        add_user(normalized, rank, secret_key, current_zone=zone)
    except Exception as e:
        logger.error(f"Ошибка регистрации {normalized}: {e}")
        return {'success': False, 'message': f'Ошибка БД: {str(e)}'}, 500

    nfc_token = _make_nfc_token(normalized, rank, zone)
    logger.info(f"Мобильная регистрация: {normalized}, ранг {rank}, зона {zone}, токен={'да' if nfc_token else 'нет'}")
    return {
        'success': True,
        'uid': normalized,
        'rank': rank,
        'zone': zone,
        'token': nfc_token,
        'message': f'Пользователь {normalized} зарегистрирован (ранг {rank})'
    }


@app.route('/api/token/inspect', methods=['POST'])
@csrf.exempt
def api_token_inspect():
    """
    API: Расшифровать NFC-токен (для демонстрации на защите).
    Показывает содержимое токена — только сервер с правильным ключом может это сделать.
    """
    data = request.json or {}
    token_str = data.get('token', '').strip()
    if not token_str:
        return {'success': False, 'message': 'Токен не передан'}, 400
    payload = _decode_nfc_token(token_str)
    if payload is None:
        return {'success': False, 'message': 'Токен повреждён или ключ неверен'}, 400
    return {'success': True, 'payload': payload}


@app.errorhandler(404)
def not_found(error):
    """Обработчик 404"""
    flash("Страница не найдена", "error")
    return redirect(url_for('index'))


@app.errorhandler(500)
def internal_error(error):
    """Обработчик 500"""
    logger.error(f"Внутренняя ошибка сервера: {error}")
    flash("Внутренняя ошибка сервера", "error")
    return redirect(url_for('index'))


if __name__ == '__main__':
    logger.info("Запуск сервера СКУД на порту 5000...")
    app.run(debug=True, host='0.0.0.0', port=5001)
