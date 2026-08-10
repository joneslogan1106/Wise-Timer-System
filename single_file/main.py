from flask import Flask, render_template, request, redirect, jsonify, send_from_directory
import threading
import time
import json
import os
from datetime import datetime

app = Flask(__name__)

# ----- TIMER STATE -----
timer_settings = [
    ["period_1", 960],
    ["period_2", 960],
    ["period_3", 960],
    ["period_4", 960]
]

state = {
    'settings': timer_settings,
    'current_index': 0,
    'remaining': timer_settings[0][1] if timer_settings else 0,
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
    """Background thread that updates the timer every second"""
    while True:
        with state_lock:
            if state['running'] and state['remaining'] > 0:
                state['remaining'] -= 1
                state['last_updated'] = datetime.now().isoformat()
                print(f"Timer: {state['remaining']} seconds remaining")  # Debug log
                
                # When timer reaches 0, advance to next period
                if state['remaining'] == 0:
                    if state['current_index'] < len(state['settings']) - 1:
                        state['current_index'] += 1
                        state['remaining'] = state['settings'][state['current_index']][1]
                        print(f"Advanced to period {state['current_index'] + 1}")
                    else:
                        state['running'] = False
                        print("Timer finished - all periods complete")
            elif state['running'] and state['remaining'] <= 0:
                # If running but remaining is 0 or negative, stop
                state['running'] = False
                print("Timer stopped - remaining is 0")
        time.sleep(1)

# Start timer thread
timer_thread = threading.Thread(target=timer_loop, daemon=True)
timer_thread.start()
print("✅ Timer loop started")

# ----- SERVE STATIC FILES -----
@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

# ----- ROUTES -----

# ---- Controller Route ----
@app.route('/')
def index():
    with state_lock:
        return render_template('controller.html', 
                               settings=state['settings'], 
                               convert_seconds_to_time=convert_seconds_to_time)

# ---- Display Route ----
@app.route('/display')
def display():
    return render_template('display.html')

# ---- Period Management Routes ----
@app.route('/increase', methods=['POST'])
def increase():
    period_id = int(request.form.get('period_number'))
    time_to_add = convert_time_to_seconds(request.form.get('increase_time'))
    with state_lock:
        if 0 <= period_id - 1 < len(state['settings']):
            state['settings'][period_id - 1][1] += time_to_add
            # If this is the current period, update remaining time too
            if period_id - 1 == state['current_index'] and not state['running']:
                state['remaining'] = state['settings'][period_id - 1][1]
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
            # If this is the current period, update remaining time too
            if period_id - 1 == state['current_index'] and not state['running']:
                state['remaining'] = state['settings'][period_id - 1][1]
    return redirect('/')

@app.route('/set-time', methods=['POST'])
def set_time():
    period_id = int(request.form.get('period_number'))
    new_time = convert_time_to_seconds(request.form.get('set_time'))
    with state_lock:
        if 0 <= period_id - 1 < len(state['settings']):
            state['settings'][period_id - 1][1] = new_time
            # If this is the current period, update remaining time too
            if period_id - 1 == state['current_index'] and not state['running']:
                state['remaining'] = state['settings'][period_id - 1][1]
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
    return redirect('/')

# ---- Timer Control Routes ----
@app.route('/start', methods=['POST'])
def start_timer():
    with state_lock:
        if state['remaining'] <= 0 and state['current_index'] < len(state['settings']):
            state['remaining'] = state['settings'][state['current_index']][1]
        state['running'] = True
        print(f"Timer started - Period {state['current_index'] + 1}, {state['remaining']} seconds")
    return redirect('/')

@app.route('/pause', methods=['POST'])
def pause_timer():
    with state_lock:
        state['running'] = False
        print(f"Timer paused at {state['remaining']} seconds")
    return redirect('/')

@app.route('/reset', methods=['POST'])
def reset_timer():
    with state_lock:
        state['running'] = False
        if state['current_index'] < len(state['settings']):
            state['remaining'] = state['settings'][state['current_index']][1]
            print(f"Timer reset to {state['remaining']} seconds")
    return redirect('/')

@app.route('/next', methods=['POST'])
def next_period():
    with state_lock:
        if state['current_index'] < len(state['settings']) - 1:
            state['current_index'] += 1
            state['remaining'] = state['settings'][state['current_index']][1]
            state['running'] = False
            print(f"Moved to period {state['current_index'] + 1}")
    return redirect('/')

@app.route('/prev', methods=['POST'])
def prev_period():
    with state_lock:
        if state['current_index'] > 0:
            state['current_index'] -= 1
            state['remaining'] = state['settings'][state['current_index']][1]
            state['running'] = False
            print(f"Moved to period {state['current_index'] + 1}")
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
def get_state():
    with state_lock:
        return jsonify({
            'settings': state['settings'],
            'current_index': state['current_index'],
            'remaining': state['remaining'],
            'running': state['running']
        })

# ---- Health Check ----
@app.route('/health')
def health():
    return 'OK', 200

# ----- MAIN -----
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)