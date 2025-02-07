import json
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
        """Send drawing data to all clients except the sender."""
        for client in self.clients:
            if client != sender_socket:
                try:
                    client.sendall(json.dumps(data).encode())  # Broadcast as JSON
                except Exception as e:
                    print(f"Error sending data to client {client.getpeername()}: {e}")
                    self.clients.remove(client)

    def handle_client(self, client_socket):
        """Handle communication with a single client."""
        self.clients.append(client_socket)
        while True:
            try:
                data = client_socket.recv(1024)
                if data:
                    data = json.loads(data)
                    self.broadcast(data, client_socket)  # Broadcast received data
                else:
                    break
            except Exception as e:
                print(f"Error handling client {client_socket.getpeername()}: {e}")
                break
        client_socket.close()
        self.clients.remove(client_socket)

    def start(self):
        """Accept new clients and start a thread for each."""
        while True:
            client_socket, _ = self.server_socket.accept()
            print(f"New client connected: {client_socket.getpeername()}")
            threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()


if __name__ == "__main__":
    server = WhiteboardServer()
    server.start()
