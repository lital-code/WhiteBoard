import sys
import socket
import threading
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QPixmap, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget

class WhiteboardClient(QMainWindow):
    def __init__(self, host="127.0.0.1", port=12345):
        super().__init__()

        self.setWindowTitle("Whiteboard Client")
        self.setGeometry(100, 100, 800, 600)

        # Network setup
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((host, port))

        # UI setup
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        self.canvas = QLabel()
        self.canvas.setFixedSize(800, 500)
        self.pixmap = QPixmap(self.canvas.size())
        self.pixmap.fill(Qt.GlobalColor.white)
        self.canvas.setPixmap(self.pixmap)
        self.layout.addWidget(self.canvas)

        self.drawing = False
        self.last_point = QPoint()
        self.pen_color = Qt.GlobalColor.black

        # Start listening for incoming data
        threading.Thread(target=self.receive_data, daemon=True).start()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            self.last_point = event.position().toPoint()

    def mouseMoveEvent(self, event):
        if self.drawing and event.buttons() == Qt.MouseButton.LeftButton:
            current_point = event.position().toPoint()
            self.draw_line(self.last_point, current_point, self.pen_color)
            self.last_point = current_point

            # Send drawing data to the server
            data = f"{self.last_point.x()},{self.last_point.y()},{current_point.x()},{current_point.y()},{self.pen_color}"
            self.client_socket.\
                sendall(data.encode())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = False

    def draw_line(self, start, end, color):
        painter = QPainter(self.pixmap)
        pen = QPen(color, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(start, end)
        painter.end()
        self.canvas.setPixmap(self.pixmap)

    def receive_data(self):
        while True:
            try:
                data = self.client_socket.recv(1024).decode()
                if data:
                    x1, y1, x2, y2, color = data.split(",")
                    start_point = QPoint(int(x1), int(y1))
                    end_point = QPoint(int(x2), int(y2))
                    self.draw_line(start_point, end_point, Qt.GlobalColor(int(color)))
            except:
                break

if __name__ == "__main__":
    app = QApplication(sys.argv)
    client = WhiteboardClient()
    client.show()
    sys.exit(app.exec())
