import sys
import socket
import threading
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget, QFileDialog, QColorDialog

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

        # Buttons
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_image)
        self.layout.addWidget(self.save_button)

        self.color_button = QPushButton("Choose Color")
        self.color_button.clicked.connect(self.choose_color)
        self.layout.addWidget(self.color_button)

        # Drawing state
        self.drawing = False
        self.last_point = QPoint()
        self.pen_color = QColor(Qt.GlobalColor.black)

        # Start listening for incoming data
        threading.Thread(target=self.receive_data, daemon=True).start()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            self.last_point = QPoint(int(event.position().x()), int(event.position().y()))

    def mouseMoveEvent(self, event):
        if self.drawing and event.buttons() == Qt.MouseButton.LeftButton:
            current_point = QPoint(int(event.position().x()), int(event.position().y()))

            # Draw on the local canvas
            self.draw_line(self.last_point, current_point, self.pen_color)

            # Send drawing data to the server
            data = f"{self.last_point.x()},{self.last_point.y()},{current_point.x()},{current_point.y()},{self.pen_color.rgb()}"
            try:
                self.client_socket.sendall(data.encode())
            except Exception as e:
                print(f"Error sending data: {e}")

            self.last_point = current_point

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = False

    def save_image(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Image", "", "PNG Files (*.png);;All Files (*)", options=options)
        if file_path:
            self.pixmap.save(file_path, "PNG")

    def choose_color(self):
        color = QColorDialog.getColor(initial=self.pen_color, parent=self, title="Select Pen Color")
        if color.isValid():
            self.pen_color = color

    def draw_line(self, start, end, color):
        """Draw a line on the local canvas."""
        painter = QPainter(self.pixmap)
        pen = QPen(color, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(start, end)
        painter.end()
        self.canvas.setPixmap(self.pixmap)

    def receive_data(self):
        """Receive drawing data from the server."""
        while True:
            try:
                data = self.client_socket.recv(1024)
                if data:
                    print(f"Received data: {data.decode()}")  # Debug log
                    # Parse the data
                    x1, y1, x2, y2, color = data.decode().split(",")
                    start_point = QPoint(int(x1), int(y1))
                    end_point = QPoint(int(x2), int(y2))
                    color = QColor(int(color))  # Convert RGB integer to QColor
                    self.draw_line(start_point, end_point, color)
            except Exception as e:
                print(f"Error receiving data: {e}")
                break

if __name__ == "__main__":
    app = QApplication(sys.argv)
    client = WhiteboardClient()
    client.show()
    sys.exit(app.exec())
