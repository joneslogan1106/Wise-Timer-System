from flask import Flask, render_template, redirect, request, jsonify
import requests
import ast
import os

app = Flask(__name__)

SOCKET_HOST = os.environ.get('SOCKET_HOST', 'localhost')
SOCKET_PORT = int(os.environ.get('SOCKET_PORT', 5000))

def convert_seconds_to_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02}:{minutes:02}:{secs:02}"

def convert_time_to_seconds(time_str):
    hours, minutes, seconds = map(int, time_str.split(':'))
    return hours * 3600 + minutes * 60 + seconds

def send_command(cmd, args=None):
    """Send command via HTTP POST to the socket server"""
    try:
        resp = requests.post(
            f'http://{SOCKET_HOST}:{SOCKET_PORT}/socket',
            json={'command': cmd, 'args': args or []},
            timeout=5
        )
        return resp.json()
    except Exception as e:
        print(f"Error: {e}")
        return None

# ----- Routes -----
@app.route('/increase', methods=['POST'])
def increase():
    period_id = int(request.form.get('period_number'))
    time_to_add = convert_time_to_seconds(request.form.get('increase_time'))
    send_command('INCREASE_PERIOD', [period_id-1, time_to_add])
    return redirect('/')

@app.route('/set-time', methods=['POST'])
def set_time():
    period_id = int(request.form.get('period_number'))
    new_time = convert_time_to_seconds(request.form.get('set_time'))
    send_command('SET_PERIOD_TIME', [period_id-1, new_time])
    return redirect('/')

@app.route('/decrease', methods=['POST'])
def decrease():
    period_id = int(request.form.get('period_number'))
    time_to_subtract = convert_time_to_seconds(request.form.get('decrease_time'))
    send_command('DECREASE_PERIOD', [period_id-1, time_to_subtract])
    return redirect('/')

@app.route('/remove_period', methods=['POST'])
def remove():
    period_id = int(request.form.get('period_number'))
    send_command('REMOVE_PERIOD', [period_id-1])
    return redirect('/')

@app.route('/create_period', methods=['POST'])
def create():
    send_command('CREATE_PERIOD')
    return redirect('/')

@app.route('/end_server', methods=['POST'])
def end_server_route():
    # Just redirect - the server is now a web service
    return redirect('/')

@app.route('/start', methods=['POST'])
def start_timer():
    send_command('START_TIMER')
    return redirect('/')

@app.route('/pause', methods=['POST'])
def pause_timer():
    send_command('PAUSE_TIMER')
    return redirect('/')

@app.route('/reset', methods=['POST'])
def reset_timer():
    send_command('RESET_TIMER')
    return redirect('/')

@app.route('/next', methods=['POST'])
def next_period():
    send_command('NEXT_PERIOD')
    return redirect('/')

@app.route('/prev', methods=['POST'])
def prev_period():
    send_command('PREV_PERIOD')
    return redirect('/')

@app.route('/timer-state')
def timer_state():
    resp = send_command('GET_STATE')
    if resp is None:
        return jsonify({'error': 'Server unavailable'}), 503
    return jsonify(resp)

@app.route("/")
def index():
    try:
        # Get settings via HTTP
        resp = send_command('GET_STATE')
        if resp and resp.get('status') != 'error':
            settings = resp.get('settings', [])
        else:
            settings = []
    except:
        return "Timer server is not running. Please start the server first."

    return render_template('controller.html', 
                           settings=settings, 
                           convert_seconds_to_time=convert_seconds_to_time)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)