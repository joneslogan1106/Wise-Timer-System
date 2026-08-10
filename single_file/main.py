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

# ----- API ENDPOINTS -----
@app.route('/api/state')
def api_state():
    with state_lock:
        return jsonify({
            'settings': state['settings'],
            'current_index': state['current_index'],
            'remaining': state['remaining'],
            'running': state['running'],
            'current_period': state['current_index'] + 1 if state['settings'] else 0
        })

@app.route('/api/command', methods=['POST'])
def api_command():
    data = request.json
    cmd = data.get('command', '')
    args = data.get('args', [])
    
    with state_lock:
        try:
            if cmd == 'START_TIMER':
                if state['remaining'] <= 0 and state['current_index'] < len(state['settings']):
                    state['remaining'] = state['settings'][state['current_index']][1]
                state['running'] = True
                return jsonify({'status': 'ok'})
            
            elif cmd == 'PAUSE_TIMER':
                state['running'] = False
                return jsonify({'status': 'ok'})
            
            elif cmd == 'RESET_TIMER':
                state['running'] = False
                if state['current_index'] < len(state['settings']):
                    state['remaining'] = state['settings'][state['current_index']][1]
                return jsonify({'status': 'ok'})
            
            elif cmd == 'NEXT_PERIOD':
                if state['current_index'] < len(state['settings']) - 1:
                    state['current_index'] += 1
                    state['remaining'] = state['settings'][state['current_index']][1]
                    state['running'] = False
                return jsonify({'status': 'ok'})
            
            elif cmd == 'PREV_PERIOD':
                if state['current_index'] > 0:
                    state['current_index'] -= 1
                    state['remaining'] = state['settings'][state['current_index']][1]
                    state['running'] = False
                return jsonify({'status': 'ok'})
            
            elif cmd == 'INCREASE_PERIOD':
                if len(args) >= 2:
                    period_id, time_to_add = args
                    if 0 <= period_id < len(state['settings']):
                        state['settings'][period_id][1] += time_to_add
                return jsonify({'status': 'ok'})
            
            elif cmd == 'DECREASE_PERIOD':
                if len(args) >= 2:
                    period_id, time_to_sub = args
                    if 0 <= period_id < len(state['settings']):
                        state['settings'][period_id][1] -= time_to_sub
                        if state['settings'][period_id][1] < 0:
                            state['settings'][period_id][1] = 0
                return jsonify({'status': 'ok'})
            
            elif cmd == 'SET_PERIOD_TIME':
                if len(args) >= 2:
                    period_id, new_time = args
                    if 0 <= period_id < len(state['settings']):
                        state['settings'][period_id][1] = new_time
                return jsonify({'status': 'ok'})
            
            elif cmd == 'REMOVE_PERIOD':
                if len(args) >= 1:
                    period_id = args[0]
                    if 0 <= period_id < len(state['settings']):
                        # Adjust current_index if needed
                        if period_id < state['current_index']:
                            state['current_index'] -= 1
                        elif period_id == state['current_index']:
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
                        state['settings'].pop(period_id)
                        for i in range(period_id, len(state['settings'])):
                            state['settings'][i][0] = f"period_{i+1}"
                return jsonify({'status': 'ok'})
            
            elif cmd == 'CREATE_PERIOD':
                new_num = len(state['settings']) + 1
                state['settings'].append([f"period_{new_num}", 0])
                return jsonify({'status': 'ok'})
            
            else:
                return jsonify({'status': 'error', 'message': 'Unknown command'}), 400
                
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

# ----- WEB PAGES -----
@app.route('/')
def controller():
    return render_template('controller.html', convert_seconds_to_time=convert_seconds_to_time)

@app.route('/display')
def display():
    return render_template('timer.html', convert_seconds_to_time=convert_seconds_to_time)

@app.route('/health')
def health():
    return 'OK', 200

# ----- MAIN -----
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)