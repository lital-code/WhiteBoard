import socket
import threading

class WhiteboardServer:
    def __init__(self, host="127.0.0.1", port=12345):
        self.clients = []
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((host, port))
        self.server_socket.listen(5)
        print(f"Server listening on {host}:{port}")

    def broadcast(self, data, sender_socket):
        for client in self.clients:
            if client != sender_socket:
                try:
                    client.sendall(data)
                except:
                    self.clients.remove(client)

    def handle_client(self, client_socket):
        while True:
            try:
                data = client_socket.recv(1024)
                print(data)
                if data:
                    self.broadcast(data, client_socket)
                else:
                    break
            except:
                break
        client_socket.close()
        self.clients.remove(client_socket)

    def start(self):
        while True:
            client_socket, _ = self.server_socket.accept()
            print("New connection established.")
            self.clients.append(client_socket)
            threading.Thread(target=self.handle_client, args=(client_socket,)).start()

if __name__ == "__main__":
    server = WhiteboardServer()
    server.start()
