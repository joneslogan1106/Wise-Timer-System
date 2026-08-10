import socket
import ast
import threading
import time
import json
import os
from copy import deepcopy
from flask import Flask

# ----- FLASK HEALTH CHECK (keeps Render happy) -----
app = Flask(__name__)

@app.route('/')
@app.route('/health')
def health():
    return 'OK', 200

def run_health_server():
    """Run Flask health check on Render's assigned port"""
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# Start health check in a separate thread
health_thread = threading.Thread(target=run_health_server, daemon=True)
health_thread.start()
print("✅ Health check server started")

# ----- ORIGINAL SOCKET SERVER CODE (unchanged) -----
HOST = '0.0.0.0'
SOCKET_PORT = int(os.environ.get('SOCKET_PORT', 9981))  # Different port for socket

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

timer_thread = threading.Thread(target=timer_loop, daemon=True)
timer_thread.start()
print("✅ Timer loop started")

def handle_client(conn, addr):
    global state, running_server
    with conn:
        print('Connected by', addr)
        while True:
            try:
                data = conn.recv(1024)
                if not data:
                    break
            except:
                break
            msg = data.decode().strip()
            print("Received:", msg)
            
            try:
                if msg.startswith("INCREASE PERIOD:"):
                    period_id, time_to_add = ast.literal_eval(msg[17:])
                    with state_lock:
                        if 0 <= period_id < len(state['settings']):
                            state['settings'][period_id][1] += time_to_add
                    conn.sendall(b"CONNECTION OK")

                elif msg.startswith("DECREASE PERIOD:"):
                    period_id, time_to_sub = ast.literal_eval(msg[17:])
                    with state_lock:
                        if 0 <= period_id < len(state['settings']):
                            state['settings'][period_id][1] -= time_to_sub
                    conn.sendall(b"CONNECTION OK")

                elif msg.startswith("SET PERIOD TIME:"):
                    period_id, new_time = ast.literal_eval(msg[17:])
                    with state_lock:
                        if 0 <= period_id < len(state['settings']):
                            state['settings'][period_id][1] = new_time
                    conn.sendall(b"CONNECTION OK")

                elif msg.startswith("REMOVE PERIOD:"):
                    period_id = int(msg[15:])
                    with state_lock:
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
                    conn.sendall(b"CONNECTION OK")

                elif msg == "CREATE PERIOD":
                    with state_lock:
                        new_num = len(state['settings']) + 1
                        state['settings'].append([f"period_{new_num}", 0])
                    conn.sendall(b"CONNECTION OK")

                elif msg == "REQUEST TIMER SETTINGS":
                    settings_copy = deepcopy(state['settings'])
                    conn.sendall(("CONTROLLER:" + str(settings_copy)).encode())
                    conn.sendall(b"CONNECTION OK")

                elif msg == "END TIMER SERVER":
                    conn.sendall(b"STOP")
                    running_server = False
                    conn.close()
                    break

                elif msg == "START TIMER":
                    with state_lock:
                        if state['remaining'] <= 0 and state['current_index'] < len(state['settings']):
                            state['remaining'] = state['settings'][state['current_index']][1]
                        state['running'] = True
                    conn.sendall(b"CONNECTION OK")

                elif msg == "PAUSE TIMER":
                    with state_lock:
                        state['running'] = False
                    conn.sendall(b"CONNECTION OK")

                elif msg == "RESET TIMER":
                    with state_lock:
                        state['running'] = False
                        if state['current_index'] < len(state['settings']):
                            state['remaining'] = state['settings'][state['current_index']][1]
                    conn.sendall(b"CONNECTION OK")

                elif msg == "NEXT PERIOD":
                    with state_lock:
                        if state['current_index'] < len(state['settings']) - 1:
                            state['current_index'] += 1
                            state['remaining'] = state['settings'][state['current_index']][1]
                            state['running'] = False
                    conn.sendall(b"CONNECTION OK")

                elif msg == "PREV PERIOD":
                    with state_lock:
                        if state['current_index'] > 0:
                            state['current_index'] -= 1
                            state['remaining'] = state['settings'][state['current_index']][1]
                            state['running'] = False
                    conn.sendall(b"CONNECTION OK")

                elif msg == "REQUEST TIMER STATE":
                    with state_lock:
                        resp = {
                            'settings': state['settings'],
                            'current_index': state['current_index'],
                            'remaining': state['remaining'],
                            'running': state['running']
                        }
                    conn.sendall(json.dumps(resp).encode())
                    conn.sendall(b"CONNECTION OK")

                else:
                    conn.sendall(b"UNKNOWN COMMAND")
                    
            except Exception as e:
                print(f"Error: {e}")
                conn.sendall(b"ERROR: " + str(e).encode())
        print('Disconnected from', addr)

# Start socket server on separate port
print(f"🚀 Starting socket server on {HOST}:{SOCKET_PORT}")
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, SOCKET_PORT))
    s.listen(5)
    print(f"✅ Socket server running on port {SOCKET_PORT}")
    while running_server:
        try:
            conn, addr = s.accept()
            client_thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            client_thread.start()
        except Exception as e:
            print(f"Accept error: {e}")
            break
    print("Server shut down")