import json
import os
import socket
import sys
import threading

from PyQt6.QtCore import QByteArray, QBuffer, QIODevice
from PyQt6.QtGui import QPixmap, QImage
from datetime import datetime

from Tools import receive_big_data, byte_array_to_image, send_big_data


class WhiteboardServer:
    def __init__(self, server_host="127.0.0.1",multicast_group = "224.1.1.1", multicast_group_port=5000,drawing_port=5001,secondary_port = 5002):
        self.clients = []

        self.multicast_group = multicast_group
        self.multicast_group_port = multicast_group_port

        #create a UDP socket for unicast messages and multicast
        self.drawing_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.drawing_socket.bind(('', drawing_port))
        # Set the TTL (Time-To-Live) to 1 so it stays within local network
        self.drawing_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)


        print(f"Drawing server listening on {server_host}:{drawing_port}")

        # create a secondary TCP socket which will send peripheral data to the server (such as files, brush settings,etc.)
        self.secondary_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.secondary_socket.bind((server_host, secondary_port))
        self.secondary_socket.listen(5)
        print(f"secondary server listening on {server_host}:{drawing_port}")

    def start(self):
        """start the server."""
        self.start_drawing_server()
        self.start_secondary_server()

    def start_drawing_server(self):
        """Start drawing server."""
        drawing_thread = threading.Thread(target=self.handle_drawing_data)
        drawing_thread.start()

    def start_secondary_server(self):
        """Start secondary server."""
        while True:
            client, _ = server.secondary_socket.accept()
            self.clients.append(client)
            secondary_thread = threading.Thread(target=self.handle_secondary_data,args=(client,))
            secondary_thread.start()

    def handle_drawing_data(self):
        """handle incoming drawing data and sending it to the multicast group."""
        while True:
            data,client_addr = self.drawing_socket.recvfrom(1024)
            print(f"[Server] Received drawing data from {client_addr}: {data.decode()}")

            # Multicast the drawing data to all other clients
            self.drawing_socket.sendto(data, (self.multicast_group, self.multicast_group_port))
            print("[Server] Multicasting drawing data to all clients")

    def handle_secondary_data(self,client):
        """Handle communication with a single files client."""
        while True:
            try:
                data = client.recv(1024)
                if data.decode():
                    data = json.loads(data.decode())
                    if data["action"] == "save":
                        self.save_board(client)
                    elif data["action"] == "get_boards":
                        self.get_boards(client)
                    elif data["action"] == "delete_board":
                        self.delete_board(data["data"])
                    elif data["action"] == "disconnect":
                        break
                    elif data.get("action") == "update brush":
                        self.update_brush(client, data.get("data"))
            except Exception as e:
                print(f"Error handling client {client.getpeername()}: {e}")
                break
        client.close()

    def update_brush(self,sender_client, brush_settings):
        for client in self.clients:
            if client != sender_client:
                client.send(json.dumps(brush_settings).encode())
        return

    def save_board(self,client):
        data = receive_big_data(client)
        print("Finished receiving board")

        save_dir = "Saved Boards"
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)  # Create the directory if it doesn't exist

        file_path = os.path.join(save_dir, f"{str(datetime.now()).replace(':', '')}.png")
        print(f"Saving board to {file_path}")

        pixmap = byte_array_to_image(data)

        if not pixmap.isNull():
            pixmap.save(file_path)
        else:
            print("Error: Received empty or corrupted pixmap")


    def get_boards(self,client):
        save_dir = "Saved Boards"
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)  # Create the directory if it doesn't exist

        dir_path = os.path.join(save_dir)
        client.sendall(str(len(os.listdir(dir_path))).encode())
        for filename in os.listdir(dir_path):
            with open(os.path.join(dir_path, filename), 'rb') as f:  # open in readonly mode
                # image = QImage()
                # image.loadFromData(f.read())
                client.send(filename.encode('utf-8'))
                client.recv(1024)
                send_big_data(socket,f.read())

    def delete_board(self,name):
        save_dir = "Saved Boards"
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)  # Create the directory if it doesn't exist
        file_path = os.path.join(save_dir,name)
        os.remove(file_path)


if __name__ == "__main__":
    server = WhiteboardServer()
    server.start()
