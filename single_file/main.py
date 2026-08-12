from flask import Flask, render_template, request, redirect, jsonify, send_from_directory, make_response
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
timer_thread = None
timer_running = True

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
        else:
            return int(time_str)
    except:
        return 0

# ----- TIMER LOOP (Background Thread) -----
def timer_loop():
    global timer_running
    print("🔄 Timer loop thread started")
    
    while timer_running:
        try:
            with state_lock:
                if state['running'] and state['remaining'] > 0:
                    state['remaining'] -= 1
                    state['last_updated'] = datetime.now().isoformat()
                    print(f"⏱️ Timer: {state['remaining']}s, Period: {state['current_index'] + 1}")
                    
                    if state['remaining'] == 0:
                        if state['current_index'] < len(state['settings']) - 1:
                            state['current_index'] += 1
                            state['remaining'] = state['settings'][state['current_index']][1]
                            state['running'] = False
                            print(f"➡️ Advanced to period {state['current_index'] + 1} (paused)")
                        else:
                            state['running'] = False
                            print("⏹️ Timer finished")
                elif state['running'] and state['remaining'] <= 0:
                    state['running'] = False
                    print("⏹️ Timer stopped")
        except Exception as e:
            print(f"❌ Timer loop error: {e}")
        
        time.sleep(1)
    
    print("🔄 Timer loop thread stopped")

def start_timer_thread():
    """Start the timer thread if it's not running"""
    global timer_thread
    if timer_thread is None or not timer_thread.is_alive():
        timer_thread = threading.Thread(target=timer_loop, daemon=True)
        timer_thread.start()
        print("✅ Timer thread started")
        return True
    return False

# Start timer thread on app startup
start_timer_thread()

# ----- SERVE STATIC FILES -----
@app.route('/static/<path:path>')
def serve_static(path):
    response = make_response(send_from_directory('static', path))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# ----- ROUTES -----

# ---- Controller Route ----
@app.route('/')
def index():
    # Ensure timer thread is running
    start_timer_thread()
    
    with state_lock:
        response = make_response(render_template('controller.html', 
                               settings=state['settings'], 
                               convert_seconds_to_time=convert_seconds_to_time))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

# ---- Display Route ----
@app.route('/display')
def display():
    # Ensure timer thread is running
    start_timer_thread()
    
    response = make_response(render_template('display.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# ---- Period Management Routes ----
@app.route('/increase', methods=['POST'])
def increase():
    start_timer_thread()
    
    period_id = int(request.form.get('period_number'))
    time_to_add = convert_time_to_seconds(request.form.get('increase_time'))
    with state_lock:
        if 0 <= period_id - 1 < len(state['settings']):
            state['settings'][period_id - 1][1] += time_to_add
            if period_id - 1 == state['current_index']:
                state['remaining'] += time_to_add
    return redirect('/')

@app.route('/decrease', methods=['POST'])
def decrease():
    start_timer_thread()
    
    period_id = int(request.form.get('period_number'))
    time_to_subtract = convert_time_to_seconds(request.form.get('decrease_time'))
    with state_lock:
        if 0 <= period_id - 1 < len(state['settings']):
            state['settings'][period_id - 1][1] -= time_to_subtract
            if state['settings'][period_id - 1][1] < 0:
                state['settings'][period_id - 1][1] = 0
            if period_id - 1 == state['current_index']:
                state['remaining'] -= time_to_subtract
                if state['remaining'] < 0:
                    state['remaining'] = 0
    return redirect('/')

@app.route('/set-time', methods=['POST'])
def set_time():
    start_timer_thread()
    
    period_id = int(request.form.get('period_number'))
    new_time = convert_time_to_seconds(request.form.get('set_time'))
    with state_lock:
        if 0 <= period_id - 1 < len(state['settings']):
            state['settings'][period_id - 1][1] = new_time
            if period_id - 1 == state['current_index']:
                state['remaining'] = new_time
    return redirect('/')

@app.route('/remove_period', methods=['POST'])
def remove_period():
    start_timer_thread()
    
    period_id = int(request.form.get('period_number'))
    with state_lock:
        if 0 <= period_id - 1 < len(state['settings']):
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
            for i in range(period_id - 1, len(state['settings'])):
                state['settings'][i][0] = f"period_{i+1}"
    return redirect('/')

@app.route('/create_period', methods=['POST'])
def create_period():
    start_timer_thread()
    
    with state_lock:
        new_num = len(state['settings']) + 1
        state['settings'].append([f"period_{new_num}", 0])
    return redirect('/')

@app.route('/end_server', methods=['POST'])
def end_server():
    return redirect('/')

# ---- Import / Export Periods ----
@app.route('/export-periods')
def export_periods():
    with state_lock:
        data = {'settings': state['settings']}
    response = make_response(jsonify(data))
    response.headers['Content-Disposition'] = 'attachment; filename=periods.json'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

@app.route('/import-periods', methods=['POST'])
def import_periods():
    start_timer_thread()

    uploaded = request.files.get('periods_file')
    if not uploaded or uploaded.filename == '':
        return redirect('/')

    try:
        data = json.load(uploaded)
        new_settings = data.get('settings')
        if not isinstance(new_settings, list) or len(new_settings) == 0:
            print("❌ Import error: 'settings' missing or empty")
            return redirect('/')

        cleaned = []
        for i, item in enumerate(new_settings):
            if isinstance(item, (list, tuple)) and len(item) == 2:
                _, seconds = item
                seconds = int(seconds)
                if seconds < 0:
                    seconds = 0
                cleaned.append([f"period_{i + 1}", seconds])

        if not cleaned:
            print("❌ Import error: no valid periods found in file")
            return redirect('/')

        with state_lock:
            state['settings'] = cleaned
            state['current_index'] = 0
            state['remaining'] = cleaned[0][1]
            state['running'] = False
            print(f"📥 Imported {len(cleaned)} periods from JSON file")
    except Exception as e:
        print(f"❌ Import error: {e}")

    return redirect('/')

# ---- Timer Control Routes ----
@app.route('/start', methods=['POST'])
def start_timer():
    start_timer_thread()
    
    with state_lock:
        if state['remaining'] <= 0 and state['current_index'] < len(state['settings']):
            state['remaining'] = state['settings'][state['current_index']][1]
        state['running'] = True
        print(f"▶️ Timer started - Period {state['current_index'] + 1}, {state['remaining']}s")
    return redirect('/')

@app.route('/pause', methods=['POST'])
def pause_timer():
    start_timer_thread()
    
    with state_lock:
        state['running'] = False
        print(f"⏸️ Timer paused at {state['remaining']}s")
    return redirect('/')

@app.route('/reset', methods=['POST'])
def reset_timer():
    start_timer_thread()
    
    with state_lock:
        state['running'] = False
        if state['current_index'] < len(state['settings']):
            state['remaining'] = state['settings'][state['current_index']][1]
            print(f"🔄 Timer reset to {state['remaining']}s")
    return redirect('/')

@app.route('/next', methods=['POST'])
def next_period():
    start_timer_thread()
    
    with state_lock:
        if state['current_index'] < len(state['settings']) - 1:
            state['current_index'] += 1
            state['remaining'] = state['settings'][state['current_index']][1]
            state['running'] = False
            print(f"⏭️ Moved to period {state['current_index'] + 1}")
    return redirect('/')

@app.route('/prev', methods=['POST'])
def prev_period():
    start_timer_thread()
    
    with state_lock:
        if state['current_index'] > 0:
            state['current_index'] -= 1
            state['remaining'] = state['settings'][state['current_index']][1]
            state['running'] = False
            print(f"⏮️ Moved to period {state['current_index'] + 1}")
    return redirect('/')

# ---- API Endpoints (for JavaScript) ----
@app.route('/timer-state')
def timer_state():
    start_timer_thread()
    
    with state_lock:
        response_data = {
            'settings': state['settings'],
            'current_index': state['current_index'],
            'remaining': state['remaining'],
            'running': state['running'],
            'current_period': state['current_index'] + 1 if state['settings'] else 0
        }
        response = make_response(jsonify(response_data))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

@app.route('/state')
def get_state():
    start_timer_thread()
    
    with state_lock:
        response_data = {
            'settings': state['settings'],
            'current_index': state['current_index'],
            'remaining': state['remaining'],
            'running': state['running'],
            'total_periods': len(state['settings'])
        }
        response = make_response(jsonify(response_data))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

# ---- Health Check ----
@app.route('/health')
def health():
    return 'OK', 200

# ----- MAIN -----
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)