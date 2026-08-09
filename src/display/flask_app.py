from flask import Flask, render_template, jsonify
import requests
import os

app = Flask(__name__)

SOCKET_HOST = os.environ.get('SOCKET_HOST', 'localhost')
SOCKET_PORT = int(os.environ.get('SOCKET_PORT', 5000))

def convert_seconds_to_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02}:{minutes:02}:{secs:02}"

def fetch_timer_state():
    try:
        resp = requests.get(f'http://{SOCKET_HOST}:{SOCKET_PORT}/socket', 
                           json={'command': 'GET_STATE'},
                           timeout=5)
        return resp.json()
    except Exception as e:
        print(f"Error fetching state: {e}")
        return None

@app.route('/')
def index():
    state = fetch_timer_state()
    if state is None or state.get('status') == 'error':
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