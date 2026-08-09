from flask import Flask, render_template
import socket
import ast

app = Flask(__name__)
HOST = '0.0.0.0'
PORT = 9980

@app.route("/")
def index():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall(b'REQUEST TIMER SETTINGS')
        data = ast.literal_eval(str(s.recv(1024), 'utf-8')[11:][:-13]) # Remove the "CONTROLLER:" prefix and evaluate as Python object, and removes the CONNECTION OK message that is sent after the first message is sent to the server
        print('Received', repr(data))
    return render_template('base.html')


app.run()