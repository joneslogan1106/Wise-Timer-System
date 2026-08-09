from flask import Flask, render_template, jsonify
import socket
import json

app = Flask(__name__)

SOCKET_HOST = os.environ.get('SOCKET_HOST', '127.0.0.1')
SOCKET_PORT = int(os.environ.get('SOCKET_PORT', 9980))

def fetch_timer_state():
    """Connect to the timer server and fetch the current state."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((SERVER_HOST, SERVER_PORT))
            s.sendall(b'REQUEST TIMER STATE')
            # Read the JSON part (first 1024 bytes should be enough)
            data = s.recv(1024)
            # The server sends JSON followed by "CONNECTION OK" – we only need the JSON.
            # Since we know the JSON ends with '}', we can split.
            parts = data.decode().split('CONNECTION OK')
            json_str = parts[0].strip()
            return json.loads(json_str)
    except Exception as e:
        print(f"Error fetching state: {e}")
        return None

@app.route('/')
def index():
    state = fetch_timer_state()
    if state is None:
        return "Timer server is not running. Please start the server first.", 503
    return render_template('timer.html', state=state)

@app.route('/state')
def state():
    state = fetch_timer_state()
    if state is None:
        return jsonify({'error': 'Server unavailable'}), 503
    return jsonify(state)

if __name__ == '__main__':
    port = int(os.environ.get('DISPLAY_PORT', 5001))
    app.run(host='0.0.0.0', port=5001, debug=False)   # Use a different port than the controller