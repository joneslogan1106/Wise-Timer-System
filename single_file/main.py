from flask import Flask, render_template, request, redirect, jsonify
import threading
import time
import json
import os
from datetime import datetime

app = Flask(__name__)

# ----- TIMER STATE -----
settings = [
    ["period_1", 960],
    ["period_2", 960],
    ["period_3", 960],
    ["period_4", 960]
]

state = {
    'settings': settings,
    'current_index': 0,
    'remaining': settings[0][1] if settings else 0,
    'running': False,
    'last_updated': datetime.now().isoformat()
}
state_lock = threading.Lock()

# ----- HELPER FUNCTIONS -----
def convert_seconds_to_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02}:{minutes:02}:{secs:02}"
    return f"{minutes:02}:{secs:02}"

def convert_time_to_seconds(time_str):
    try:
        parts = time_str.split(':')
        if len(parts) == 3:
            hours, minutes, seconds = map(int, parts)
            return hours * 3600 + minutes * 60 + seconds
        elif len(parts) == 2:
            minutes, seconds = map(int, parts)
            return minutes * 60 + seconds
    except:
        return 0
    return 0

# ----- TIMER LOOP (Background Thread) -----
def timer_loop():
    while True:
        with state_lock:
            if state['running'] and state['remaining'] > 0:
                state['remaining'] -= 1
                state['last_updated'] = datetime.now().isoformat()
                if state['remaining'] == 0:
                    if state['current_index'] < len(state['settings']) - 1:
                        state['current_index'] += 1
                        state['remaining'] = state['settings'][state['current_index']][1]
                    else:
                        state['running'] = False
        time.sleep(1)

# Start timer thread
timer_thread = threading.Thread(target=timer_loop, daemon=True)
timer_thread.start()

# ----- ROUTES -----

# ---- Controller Routes (from your controller.html) ----
@app.route('/')
def index():
    with state_lock:
        return render_template('controller.html', 
                               settings=state['settings'], 
                               convert_seconds_to_time=convert_seconds_to_time)

@app.route('/increase', methods=['POST'])
def increase():
    period_id = int(request.form.get('period_number'))
    time_to_add = convert_time_to_seconds(request.form.get('increase_time'))
    with state_lock:
        if 0 <= period_id - 1 < len(state['settings']):
            state['settings'][period_id - 1][1] += time_to_add
    return redirect('/')

@app.route('/decrease', methods=['POST'])
def decrease():
    period_id = int(request.form.get('period_number'))
    time_to_subtract = convert_time_to_seconds(request.form.get('decrease_time'))
    with state_lock:
        if 0 <= period_id - 1 < len(state['settings']):
            state['settings'][period_id - 1][1] -= time_to_subtract
            if state['settings'][period_id - 1][1] < 0:
                state['settings'][period_id - 1][1] = 0
    return redirect('/')

@app.route('/set-time', methods=['POST'])
def set_time():
    period_id = int(request.form.get('period_number'))
    new_time = convert_time_to_seconds(request.form.get('set_time'))
    with state_lock:
        if 0 <= period_id - 1 < len(state['settings']):
            state['settings'][period_id - 1][1] = new_time
    return redirect('/')

@app.route('/remove_period', methods=['POST'])
def remove_period():
    period_id = int(request.form.get('period_number'))
    with state_lock:
        if 0 <= period_id - 1 < len(state['settings']):
            # Adjust current_index if needed
            if period_id - 1 < state['current_index']:
                state['current_index'] -= 1
            elif period_id - 1 == state['current_index']:
                if state['current_index'] < len(state['settings']) - 1:
                    state['current_index'] += 1
                    state['remaining'] = state['settings'][state['current_index']][1]
                else:
                    if state['current_index'] > 0:
                        state['current_index'] -= 1
                        state['remaining'] = state['settings'][state['current_index']][1]
                    else:
                        state['current_index'] = 0
                        state['remaining'] = 0
                state['running'] = False
            state['settings'].pop(period_id - 1)
            # Renumber periods
            for i in range(period_id - 1, len(state['settings'])):
                state['settings'][i][0] = f"period_{i+1}"
    return redirect('/')

@app.route('/create_period', methods=['POST'])
def create_period():
    with state_lock:
        new_num = len(state['settings']) + 1
        state['settings'].append([f"period_{new_num}", 0])
    return redirect('/')

@app.route('/end_server', methods=['POST'])
def end_server():
    # Just redirect - the server is now a web service
    return redirect('/')

# ---- Timer Control Routes ----
@app.route('/start', methods=['POST'])
def start_timer():
    with state_lock:
        if state['remaining'] <= 0 and state['current_index'] < len(state['settings']):
            state['remaining'] = state['settings'][state['current_index']][1]
        state['running'] = True
    return redirect('/')

@app.route('/pause', methods=['POST'])
def pause_timer():
    with state_lock:
        state['running'] = False
    return redirect('/')

@app.route('/reset', methods=['POST'])
def reset_timer():
    with state_lock:
        state['running'] = False
        if state['current_index'] < len(state['settings']):
            state['remaining'] = state['settings'][state['current_index']][1]
    return redirect('/')

@app.route('/next', methods=['POST'])
def next_period():
    with state_lock:
        if state['current_index'] < len(state['settings']) - 1:
            state['current_index'] += 1
            state['remaining'] = state['settings'][state['current_index']][1]
            state['running'] = False
    return redirect('/')

@app.route('/prev', methods=['POST'])
def prev_period():
    with state_lock:
        if state['current_index'] > 0:
            state['current_index'] -= 1
            state['remaining'] = state['settings'][state['current_index']][1]
            state['running'] = False
    return redirect('/')

# ---- API Endpoints (for JavaScript) ----
@app.route('/timer-state')
def timer_state():
    with state_lock:
        return jsonify({
            'settings': state['settings'],
            'current_index': state['current_index'],
            'remaining': state['remaining'],
            'running': state['running'],
            'current_period': state['current_index'] + 1 if state['settings'] else 0
        })

@app.route('/state')
def state():
    with state_lock:
        return jsonify({
            'settings': state['settings'],
            'current_index': state['current_index'],
            'remaining': state['remaining'],
            'running': state['running']
        })

# ---- Display Route ----
@app.route('/display')
def display():
    return render_template('display.html')

# ---- Health Check ----
@app.route('/health')
def health():
    return 'OK', 200

# ----- MAIN -----
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)