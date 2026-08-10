from flask import Flask, render_template, jsonify
import socket
import json
import os

app = Flask(__name__)

SOCKET_HOST = os.environ.get('SOCKET_HOST', 'localhost')
SOCKET_PORT = int(os.environ.get('SOCKET_PORT', 9981))

def convert_seconds_to_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02}:{minutes:02}:{secs:02}"
    return f"{minutes:02}:{secs:02}"

def fetch_timer_state():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((SOCKET_HOST, SOCKET_PORT))
            s.sendall(b'REQUEST TIMER STATE')
            data = s.recv(1024)
            json_part = data.decode().split('CONNECTION OK')[0].strip()
            return json.loads(json_part)
    except Exception as e:
        print(f"Error fetching state: {e}")
        return None

@app.route('/')
def index():
    state = fetch_timer_state()
    if state is None:
        return "Timer server is not running. Please start the server first.", 503
    return render_template('timer.html', state=state, convert_seconds_to_time=convert_seconds_to_time)

@app.route('/state')
def state():
    state = fetch_timer_state()
    if state is None:
        return jsonify({'error': 'Server unavailable'}), 503
    return jsonify(state)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5001)), debug=False)