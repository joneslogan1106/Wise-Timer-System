import socket
import ast
import threading
import time
import json
from copy import deepcopy

HOST = '0.0.0.0'
PORT = int(os.environ.get('SOCKET_PORT', 9980))  # Use environment variable

# Initial settings
settings = [
    ["period_1", 960],
    ["period_2", 960],
    ["period_3", 960],
    ["period_4", 960]
]

# Timer state
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

            # Wrap command handling to catch exceptions
            try:
                if msg.startswith("INCREASE PERIOD:"):
                    period_id, time_to_add = ast.literal_eval(msg[17:])
                    with state_lock:
                        if 0 <= period_id < len(state['settings']):
                            state['settings'][period_id][1] += time_to_add
                        else:
                            raise ValueError("Invalid period ID")
                    conn.sendall(b"CONNECTION OK")

                elif msg.startswith("DECREASE PERIOD:"):
                    period_id, time_to_sub = ast.literal_eval(msg[17:])
                    with state_lock:
                        if 0 <= period_id < len(state['settings']):
                            state['settings'][period_id][1] -= time_to_sub
                        else:
                            raise ValueError("Invalid period ID")
                    conn.sendall(b"CONNECTION OK")

                elif msg.startswith("SET PERIOD TIME:"):
                    period_id, new_time = ast.literal_eval(msg[17:])
                    with state_lock:
                        if 0 <= period_id < len(state['settings']):
                            state['settings'][period_id][1] = new_time
                        else:
                            raise ValueError("Invalid period ID")
                    conn.sendall(b"CONNECTION OK")

                elif msg.startswith("REMOVE PERIOD:"):
                    period_id = int(msg[15:])
                    with state_lock:
                        if period_id < 0 or period_id >= len(state['settings']):
                            raise ValueError("Period ID out of range")
                        # Adjust current_index if needed
                        if period_id < state['current_index']:
                            state['current_index'] -= 1
                        elif period_id == state['current_index']:
                            # If we are removing the current period, move to next if possible
                            if state['current_index'] < len(state['settings']) - 1:
                                state['current_index'] += 1
                                state['remaining'] = state['settings'][state['current_index']][1]
                            else:
                                # Last period: go to previous
                                if state['current_index'] > 0:
                                    state['current_index'] -= 1
                                    state['remaining'] = state['settings'][state['current_index']][1]
                                else:
                                    # Only period left, set to 0
                                    state['current_index'] = 0
                                    state['remaining'] = 0
                            state['running'] = False
                        # Remove the period
                        state['settings'].pop(period_id)
                        # Renumber subsequent periods
                        for i in range(period_id, len(state['settings'])):
                            state['settings'][i][0] = f"period_{i+1}"
                        # If we removed the last period and current_index is now out of bounds, fix it
                        if state['current_index'] >= len(state['settings']):
                            state['current_index'] = len(state['settings']) - 1 if state['settings'] else 0
                            if state['settings']:
                                state['remaining'] = state['settings'][state['current_index']][1]
                            else:
                                state['remaining'] = 0
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
                        else:
                            state['remaining'] = 0
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
                # Catch any error, log it, and send an error response to the client
                print(f"Error handling command '{msg}': {e}")
                conn.sendall(b"ERROR: " + str(e).encode())

        print('Disconnected from', addr)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(5)
    print(f"Server listening on {HOST}:{PORT}")
    while running_server:
        try:
            conn, addr = s.accept()
            client_thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            client_thread.start()
        except Exception as e:
            print(f"Accept error: {e}")
            break
    print("Server shut down")