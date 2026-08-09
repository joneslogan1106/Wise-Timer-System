# Echo client program
import socket

HOST = '0.0.0.0'    # The remote host
PORT = 9980              # The same port as used by the server
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    while True:
        s.sendall(b'END TIMER SERVER')
        data = s.recv(1024)
        print('Received', repr(data))

        if data.decode() == "STOP":
            break
        elif data.decode() == "CONNECTION OK":
            continue