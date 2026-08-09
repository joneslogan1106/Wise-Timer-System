# Echo server program
import socket, ast

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
                if data.decode().startswith("INCREASE PERIOD:"):
                    period_id, time_to_add = ast.literal_eval(data.decode()[17:])
                    settings[period_id][1] += time_to_add
                    conn.sendall("CONNECTION OK".encode())  # Send OK after processing
                elif data.decode().startswith("DECREASE PERIOD:"):
                    period_id, time_to_add = ast.literal_eval(data.decode()[17:])
                    settings[period_id][1] -= time_to_add
                    conn.sendall("CONNECTION OK".encode())  # Send OK after processing
                elif data.decode() == "REQUEST TIMER SETTINGS":
                    conn.sendall(("CONTROLLER:" + str(settings)).encode())
                    conn.sendall("CONNECTION OK".encode())  # Send OK after data
                elif data == b"END TIMER SERVER":
                    conn.sendall("STOP".encode())
                    running = False
                    conn.close()
                    break
                