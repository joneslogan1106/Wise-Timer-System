from flask import Flask, request, jsonify
import threading
import time
import json
import os
from copy import deepcopy

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
    'running': False
}
state_lock = threading.Lock()
running_server = True

# ----- TIMER LOOP -----
def timer_loop():
    global state, running_server
    while running_server:
        with state_lock:
            if state['running'] and state['remaining'] > 0:
                state['remaining'] -= 1
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

# ----- FLASK ENDPOINTS -----
@app.route('/')
@app.route('/health')
def health():
    return 'OK', 200

@app.route('/socket', methods=['GET', 'POST'])
def socket_proxy():
    """Handle all timer commands via HTTP"""
    if request.method == 'GET':
        # GET returns current state
        with state_lock:
            return jsonify({
                'settings': state['settings'],
                'current_index': state['current_index'],
                'remaining': state['remaining'],
                'running': state['running']
            })
    
    # POST handles commands
    data = request.json
    cmd = data.get('command', '')
    args = data.get('args', [])
    
    with state_lock:
        try:
            # Timer Controls
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
            
            # Period Management
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
            
            elif cmd == 'GET_STATE':
                return jsonify({
                    'settings': state['settings'],
                    'current_index': state['current_index'],
                    'remaining': state['remaining'],
                    'running': state['running']
                })
            
            else:
                return jsonify({'status': 'error', 'message': f'Unknown command: {cmd}'}), 400
                
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

# ----- MAIN -----
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)