import json
import os
import socket
import sys
import threading

from PyQt6.QtCore import QByteArray, QBuffer, QIODevice
from PyQt6.QtGui import QPixmap, QImage
from datetime import datetime



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
                data = client_socket.recv(1024).decode()
                if data:
                    data = json.loads(data)
                    if data["type"] == "draw":
                        self.broadcast(data, client_socket)  # Broadcast received data
                    elif data["type"] == "save":
                        self.save_board(client_socket)
                    elif data["type"] == "get_boards":
                        self.get_boards(client_socket)
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

    def save_board(self, client_socket):
        data = self.receive_big_data(client_socket)
        print("Finished receiving board")

        save_dir = "Saved Boards"
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)  # Create the directory if it doesn't exist

        file_path = os.path.join(save_dir, f"{str(datetime.now()).replace(':', '')}.png")
        print(f"Saving board to {file_path}")

        pixmap = self.byte_array_to_image(data)

        if not pixmap.isNull():
            pixmap.save(file_path)
        else:
            print("Error: Received empty or corrupted pixmap")
    
    
    def receive_big_data(self,client_socket):
        # First, receive the size of the incoming data (4 bytes for an integer)
        data_received = client_socket.recv(4)  # We only expect 4 bytes for the size
        print(f"raw data received: {data_received}")
        if len(data_received) < 4:
            raise Exception("Failed to receive the full data size")

        # Convert the received size to an integer
        data_size = int.from_bytes(data_received, byteorder='big')
        print(f"Expected data size: {data_size}")

        data = b''
        while data_size > 0:
            data += client_socket.recv(1024)
            data_size -=1024
        return data
    
    def send_big_data(self,client_socket,data):
        data_size = sys.getsizeof(data)
        client_socket.send(str(data_size).encode())
        client_socket.send(data)

    def byte_array_to_pixmap(self, byte_array):
        print(f"Received byte array of size: {len(byte_array)}")

        if len(byte_array) == 0:
            print("Error: Received empty byte array")
            return None

        pixmap = QPixmap()

        # Attempt to load the image
        success = pixmap.loadFromData(byte_array, 'PNG')

        if not success:
            print("Error: Failed to load pixmap from data")
            return None

        print("Pixmap loaded successfully")
        return pixmap

    def byte_array_to_image(self, byte_array):
        # Convert byte array to QByteArray (if needed)
        byte_array = QByteArray(byte_array)
        image = QImage()

        if not image.loadFromData(byte_array):
            print("Error: Failed to load image from data")
            return None  # Or raise an exception if needed

        return image

    def image_to_byte_array(self,image:QImage):
        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(buffer, 'PNG')  # Save the pixmap as PNG format in the byte array
        return byte_array

    def get_boards(self,client_socket):
        save_dir = "Saved Boards"
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)  # Create the directory if it doesn't exist

        dir_path = os.path.join(save_dir)
        client_socket.sendall(str(len(os.listdir(dir_path))).encode())
        for filename in os.listdir(dir_path):
            with open(os.path.join(os.getcwd(), filename), 'rb') as f:  # open in readonly mode
                image = QImage()
                image.loadFromData(f)
                self.send_big_data(client_socket,self.image_to_byte_array(image))
                return

        return

if __name__ == "__main__":
    server = WhiteboardServer()
    server.start()
