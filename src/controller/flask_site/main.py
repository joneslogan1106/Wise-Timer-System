from flask import Flask, render_template, redirect, request
import socket
import ast

app = Flask(__name__)
HOST = '0.0.0.0'
PORT = 9980

def convert_seconds_to_time(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{hours:02}:{minutes:02}:{seconds:02}"
def convert_time_to_seconds(time_str):
    hours, minutes, seconds = map(int, time_str.split(':'))
    return hours * 3600 + minutes * 60 + seconds
def end_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall(b'END TIMER SERVER')

@app.route('/increase', methods=['POST'])
def increase():
    period_id = int(request.form.get('period_number'))
    time_to_add = convert_time_to_seconds(request.form.get('increase_time'))
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall(f'INCREASE PERIOD: [{period_id-1}, {time_to_add}]'.encode())
        s.recv(1024)  # Read the response to avoid broken pipe
    return redirect('/')

@app.route('/decrease', methods=['POST'])
def decrease():
    period_id = int(request.form.get('period_number'))
    time_to_subtract = convert_time_to_seconds(request.form.get('decrease_time'))
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall(f'DECREASE PERIOD: [{period_id-1}, {time_to_subtract}]'.encode())
        s.recv(1024)  # Read the response to avoid broken pipe
    return redirect('/')

@app.route('/remove_period', methods=['POST'])
def remove():
    period_id = int(request.form.get('period-input-remove'))
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall(f'REMOVE PERIOD: {period_id-1}'.encode())
        s.recv(1024)  # Read the response to avoid broken pipe
    return redirect('/')

@app.route('/end_server', methods=['POST'])
def end_server_route():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            s.sendall(b'END TIMER SERVER')
            s.recv(1024)  # Read the STOP response
    except ConnectionRefusedError:
        # Server already stopped
        pass
    except Exception as e:
        print(f"Error: {e}")
    return redirect('/')

@app.route("/")
def index():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            s.sendall(b'REQUEST TIMER SETTINGS')
            data = ast.literal_eval(str(s.recv(1024), 'utf-8')[11:][:-13]) # Remove the "CONTROLLER:" prefix and evaluate as Python object, and removes the CONNECTION OK message that is sent after the first message is sent to the server. Then converts into a usable list
        return render_template('base.html', settings=data, convert_seconds_to_time=convert_seconds_to_time)
    except ConnectionRefusedError:
        return "Timer server is not running. Please start the server first."

app.run()