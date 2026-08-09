# Echo server program
import socket

HOST = '0.0.0.0'                 # Symbolic name meaning all available interfaces
PORT = 9980              # This is the port all TLG apps will go off of
settings = [
    ["period_1", 960],
    ["period_2", 960],
    ["period_3", 960],
    ["period_4", 960]
]
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen(1)
    running = True
    while running:
        conn, addr = s.accept()
        with conn:
            print('Connected by', addr)
            while True:
                data = conn.recv(1024)
                if not data: break
                print(data.decode())
                if data.decode() == "REQUEST TIMER SETTINGS":
                    conn.sendall(("CONTROLLER:" + str(settings)).encode())
                if data == b"END TIMER SERVER": # This message will be sent if the client wants to stop the server/end the app, which this option will be available from the controller 
                    conn.sendall("STOP".encode())
                    running = False
                    break
                conn.sendall("CONNECTION OK".encode())
                