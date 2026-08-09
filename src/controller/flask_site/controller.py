from flask import Flask, render_template, redirect, request, jsonify
import socket
import ast
import json

app = Flask(__name__)
HOST = '0.0.0.0'
PORT = 5000


def convert_seconds_to_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02}:{minutes:02}:{secs:02}"

def convert_time_to_seconds(time_str):
    hours, minutes, seconds = map(int, time_str.split(':'))
    return hours * 3600 + minutes * 60 + seconds

def send_command(cmd):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            s.sendall(cmd.encode())
            resp = s.recv(1024)
            return resp.decode()
    except Exception as e:
        print(f"send_command error: {e}")
        return None

# --- Existing routes ---
@app.route('/increase', methods=['POST'])
def increase():
    period_id = int(request.form.get('period_number'))
    time_to_add = convert_time_to_seconds(request.form.get('increase_time'))
    send_command(f'INCREASE PERIOD: [{period_id-1}, {time_to_add}]')
    return redirect('/')

@app.route('/set-time', methods=['POST'])
def set_time():
    period_id = int(request.form.get('period_number'))
    new_time = convert_time_to_seconds(request.form.get('set_time'))
    send_command(f'SET PERIOD TIME: [{period_id-1}, {new_time}]')
    return redirect('/')

@app.route('/decrease', methods=['POST'])
def decrease():
    period_id = int(request.form.get('period_number'))
    time_to_subtract = convert_time_to_seconds(request.form.get('decrease_time'))
    send_command(f'DECREASE PERIOD: [{period_id-1}, {time_to_subtract}]')
    return redirect('/')

@app.route('/remove_period', methods=['POST'])
def remove():
    # ✅ FIXED: use 'period_number' (matches the input name in the template)
    period_id = int(request.form.get('period_number'))
    send_command(f'REMOVE PERIOD: {period_id-1}')
    return redirect('/')

@app.route('/create_period', methods=['POST'])
def create():
    send_command('CREATE PERIOD')
    return redirect('/')

@app.route('/end_server', methods=['POST'])
def end_server_route():
    send_command('END TIMER SERVER')
    return redirect('/')

# --- Timer control routes ---
@app.route('/start', methods=['POST'])
def start_timer():
    send_command('START TIMER')
    return redirect('/')

@app.route('/pause', methods=['POST'])
def pause_timer():
    send_command('PAUSE TIMER')
    return redirect('/')

@app.route('/reset', methods=['POST'])
def reset_timer():
    send_command('RESET TIMER')
    return redirect('/')

@app.route('/next', methods=['POST'])
def next_period():
    send_command('NEXT PERIOD')
    return redirect('/')

@app.route('/prev', methods=['POST'])
def prev_period():
    send_command('PREV PERIOD')
    return redirect('/')

# --- API endpoint for timer state ---
@app.route('/timer-state')
def timer_state():
    resp = send_command('REQUEST TIMER STATE')
    if resp is None:
        return jsonify({'error': 'Server unavailable'}), 503
    try:
        json_part = resp.split('CONNECTION OK')[0].strip()
        state = json.loads(json_part)
        state['current_period'] = state.get('current_index', 0) + 1
        return jsonify(state)
    except:
        return jsonify({'error': 'Invalid response'}), 500

# --- Main page ---
@app.route("/")
def index():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            s.sendall(b'REQUEST TIMER SETTINGS')
            data = s.recv(1024)
            raw = data.decode()
            if raw.startswith("CONTROLLER:"):
                settings_str = raw[len("CONTROLLER:"):].split('CONNECTION OK')[0].strip()
                settings = ast.literal_eval(settings_str)
            else:
                settings = []
    except:
        return "Timer server is not running. Please start the server first."

    return render_template('controller.html',
                           settings=settings,
                           convert_seconds_to_time=convert_seconds_to_time)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=False)