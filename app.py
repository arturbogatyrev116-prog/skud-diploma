"""
Веб-сервер системы СКУД
Flask приложение для управления доступом и мониторинга событий
"""
import os
import hmac
import hashlib
import datetime
import logging
import json
from typing import Optional
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_wtf.csrf import CSRFProtect
from config import (
    SECRET_KEY, MAX_ATTEMPTS_RANK_HIGH, MAX_ATTEMPTS_RANK_MEDIUM,
    MAX_ATTEMPTS_RANK_LOW, BLOCK_DURATION_MINUTES
)
from database import (
    init_db, add_user, get_user, log_access, get_zones_info,
    check_block, increment_fail, reset_fail,
    create_pending_pass, confirm_pass, cleanup_expired_passes,
    get_user_current_zone, get_user_history, get_all_users,
    get_recent_logs, delete_user, update_user, get_user_by_uid,
    get_users_with_zones, get_zone_users
)
from auth_logic import calculate_rank, is_history_valid, is_route_valid, is_context_valid

# Импорт NFC модуля (опционально)
try:
    from nfc_reader import NFCReader
    NFC_AVAILABLE = True
except ImportError:
    NFC_AVAILABLE = False
    NFCReader = None

# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['WTF_CSRF_ENABLED'] = False  # Отключено для тестирования
csrf = CSRFProtect(app)

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
        _nfc_reader = NFCReader()
        _nfc_reader.init()
    return _nfc_reader


@app.route('/')
def index():
    """Главная страница - эмуляция прохода"""
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
        conn = None
        try:
            import sqlite3
            conn = sqlite3.connect('skud.db')
            cursor = conn.cursor()
            cursor.execute("SELECT blocked_until FROM access_blocks WHERE uid = ?", (uid,))
            row = cursor.fetchone()
            if row:
                blocked_until = datetime.datetime.fromisoformat(row[0])
                remaining = max(0, int((blocked_until - datetime.datetime.now()).total_seconds()))
                flash(f"Доступ заблокирован на {remaining} секунд из-за {BLOCK_DURATION_MINUTES} минут", "error")
                logger.warning(f"Попытка доступа заблокированного пользователя: {uid}")
        finally:
            if conn:
                conn.close()
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
    
    # Определение количества попыток аутентификации на основе ранга
    user_rank = user['rank']
    if user_rank >= 8:
        max_attempts = MAX_ATTEMPTS_RANK_HIGH
    elif user_rank >= 7:
        max_attempts = MAX_ATTEMPTS_RANK_MEDIUM
    else:
        max_attempts = MAX_ATTEMPTS_RANK_LOW
    
    required_rank = zones_info[zone_to]['required_rank']
    auth_success = False
    final_combination = None
    
    # Генерация nonce и попытка аутентификации
    for attempt in range(max_attempts):
        nonce = os.urandom(16)
        # JSON-сериализация для предотвращения SQL injection
        history_bytes = json.dumps(history).encode()
        T = hmac.new(user['secret_key'].encode(), nonce + history_bytes, hashlib.sha256).digest()
        combination = [(b % 13) + 1 for b in T[:5]]
        actual_rank = calculate_rank(combination)
        
        if actual_rank == user_rank:
            auth_success = True
            final_combination = combination
            logger.debug(f"Аутентификация успешна для {uid} с попытки {attempt + 1}")
            break
    
    if not auth_success:
        is_blocked, blocked_until = increment_fail(uid)
        if is_blocked:
            flash(f"Доступ заблокирован на {BLOCK_DURATION_MINUTES} минуту из-за 3 неудачных попыток", "error")
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


@app.route('/confirm_pass/<uid>')
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
    user = get_user_by_uid(uid)
    
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
def api_nfc_status():
    """API: Проверить доступность NFC-ридера"""
    return {
        'available': NFC_AVAILABLE,
        'initialized': _nfc_reader is not None and _nfc_reader.initialized if NFC_AVAILABLE else False
    }


@app.route('/api/nfc/read', methods=['POST'])
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
    auth_success = False
    
    for attempt in range(max_attempts):
        nonce = os.urandom(16)
        history_bytes = json.dumps(history).encode()
        T = hmac.new(user['secret_key'].encode(), nonce + history_bytes, hashlib.sha256).digest()
        combination = [(b % 13) + 1 for b in T[:5]]
        actual_rank = calculate_rank(combination)
        
        if actual_rank == user_rank:
            auth_success = True
            break
    
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
    app.run(debug=True, host='0.0.0.0', port=5000)
