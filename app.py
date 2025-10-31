from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import hmac
import hashlib
import datetime
from database import (
    init_db, add_user, get_user, log_access, get_zones_info,
    check_block, increment_fail, reset_fail,
    create_pending_pass, confirm_pass, cleanup_expired_passes, get_pending_pass,
    get_user_current_zone  # ← Добавлен импорт
)
from auth_logic import calculate_rank, is_history_valid

app = Flask(__name__)
app.secret_key = os.urandom(24)
init_db()

@app.route('/')
def index():
    cleanup_expired_passes()
    return render_template('index.html')

@app.route('/users')
def users():
    import sqlite3
    conn = sqlite3.connect('skud.db')
    conn.row_factory = sqlite3.Row
    users = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    return render_template('users.html', users=users)

@app.route('/logs')
def logs():
    import sqlite3
    conn = sqlite3.connect('skud.db')
    conn.row_factory = sqlite3.Row
    logs = conn.execute("SELECT * FROM access_logs ORDER BY timestamp DESC LIMIT 100").fetchall()
    conn.close()
    return render_template('logs.html', logs=logs)

@app.route('/add_user', methods=['POST'])
def add_user_route():
    uid = request.form['uid']
    rank = int(request.form['rank'])
    name = request.form.get('name', 'User')
    secret_key = os.urandom(32)
    add_user(uid, rank, secret_key)
    flash(f"Пользователь {uid} ({name}) добавлен с рангом {rank}!", "success")
    return redirect(url_for('users'))

@app.route('/simulate_access', methods=['POST'])
def simulate_access():
    uid = request.form['uid']
    session['current_uid'] = uid  # Сохраняем UID
    zone_to = int(request.form['zone_to'])
    
    # Проверка блокировки
    is_blocked, _ = check_block(uid)
    if is_blocked:
        import sqlite3
        conn = sqlite3.connect("skud.db")
        cursor = conn.cursor()
        cursor.execute("SELECT blocked_until FROM access_blocks WHERE uid = ?", (uid,))
        blocked_until = datetime.datetime.fromisoformat(cursor.fetchone()[0])
        conn.close()
        remaining = max(0, int((blocked_until - datetime.datetime.now()).total_seconds()))
        flash(f"Доступ заблокирован на {remaining} секунд из-за 3 неудачных попыток", "error")
        return redirect(url_for('index'))
    
    user = get_user(uid)
    if not user:
        flash("Пользователь не найден!", "error")
        return redirect(url_for('index'))
    
    zones_info = get_zones_info()
    if zone_to not in zones_info:
        flash(f"Зона {zone_to} не существует!", "error")
        return redirect(url_for('index'))
    
    # === Получаем текущую зону из БД (вместо ввода из формы) ===
    current_zone = get_user_current_zone(uid)
    history = [current_zone, 0]  # ← ПЕРЕМЕННАЯ ТЕПЕРЬ ОПРЕДЕЛЕНА
    
    # Валидация истории
    history_valid, history_msg = is_history_valid(history, zones_info)
    if not history_valid:
        log_access(uid, current_zone, zone_to, False, f"Некорректная история: {history_msg}")
        flash(f"{history_msg}", "error")
        return redirect(url_for('index'))
    
    # Контекстная проверка
    if current_zone == 999 and zone_to != 0:
        reason = "Запрещён вход после выхода"
        log_access(uid, current_zone, zone_to, False, reason)
        flash(f"{reason}", "error")
        return redirect(url_for('index'))
    
    # Параметры попыток
    if user['rank'] >= 8:
        MAX_ATTEMPTS = 5000
    elif user['rank'] >= 7:
        MAX_ATTEMPTS = 1000
    else:
        MAX_ATTEMPTS = 100
    
    required_rank = zones_info[zone_to]['required_rank']
    auth_success = False
    final_combination = None
    
    for attempt in range(MAX_ATTEMPTS):
        nonce = os.urandom(16)
        history_bytes = str(history).encode()  # Используем history
        T = hmac.new(user['secret_key'], nonce + history_bytes, hashlib.sha256).digest()
        combination = [(b % 13) + 1 for b in T[:5]]
        actual_rank = calculate_rank(combination)
        
        if actual_rank == user['rank']:
            auth_success = True
            final_combination = combination
            break
    
    if not auth_success:
        is_blocked, _ = increment_fail(uid)
        if is_blocked:
            flash("Доступ заблокирован на 1 минуту из-за 3 неудачных попыток", "error")
        else:
            _, fail_count = check_block(uid)
            flash(f"Неудачная попытка ({fail_count}/3)", "error")
        return redirect(url_for('index'))
    
    # Авторизация
    if user['rank'] >= required_rank:
        # Создаём временную сессию
        create_pending_pass(uid, current_zone, zone_to)
        flash(f"Дверь открыта на 10 секунд. Подтвердите проход!", "success")
    else:
        reason = f"Недостаточно прав: ранг {user['rank']} < {required_rank}"
        log_access(uid, current_zone, zone_to, False, reason)
        flash(f"{reason}", "error")
    
    return redirect(url_for('index'))

@app.route('/confirm_pass/<uid>')
def confirm_pass_route(uid):
    print(f"DEBUG: Получен UID = {uid}")
    return f"Подтверждение для {uid} получено!"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
