from flask import Flask, render_template, redirect, request, jsonify
import socket
import ast
import os

app = Flask(__name__)

# Socket server location
SOCKET_HOST = os.environ.get('SOCKET_HOST', 'localhost')
SOCKET_PORT = int(os.environ.get('SOCKET_PORT', 9981))

def convert_seconds_to_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02}:{minutes:02}:{secs:02}"

def convert_time_to_seconds(time_str):
    parts = time_str.split(':')
    if len(parts) == 3:
        hours, minutes, seconds = map(int, parts)
        return hours * 3600 + minutes * 60 + seconds
    elif len(parts) == 2:
        minutes, seconds = map(int, parts)
        return minutes * 60 + seconds
    return 0

def send_command(cmd):
    """Send command via raw socket"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((SOCKET_HOST, SOCKET_PORT))
            s.sendall(cmd.encode())
            resp = s.recv(1024)
            return resp.decode()
    except Exception as e:
        print(f"Socket error: {e}")
        return None

# ----- Routes (unchanged) -----
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

@app.route('/timer-state')
def timer_state():
    resp = send_command('REQUEST TIMER STATE')
    if resp is None:
        return jsonify({'error': 'Server unavailable'}), 503
    try:
        json_part = resp.split('CONNECTION OK')[0].strip()
        return jsonify(json.loads(json_part))
    except:
        return jsonify({'error': 'Invalid response'}), 500

@app.route("/")
def index():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((SOCKET_HOST, SOCKET_PORT))
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

    return render_template('base.html', 
                           settings=settings, 
                           convert_seconds_to_time=convert_seconds_to_time)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)