import sys
import socket
import threading
from re import match

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget, QFileDialog, QColorDialog, QHBoxLayout
import random

SPRAY_PARTICLES = 100
SPRAY_DIAMETER = 10

class WhiteboardClient(QMainWindow):
    def __init__(self, host="127.0.0.1", port=12345):
        super().__init__()
        self.setWindowTitle("Whiteboard Client")

        # Set a minimum size to prevent the window from being too small
        self.setMinimumSize(800, 600)

        # Network setup
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((host, port))

        # UI setup
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        # Canvas setup
        self.canvas = QLabel()
        self.canvas.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.layout.addWidget(self.canvas)

        # Button layout setup
        self.button_layout = QHBoxLayout()
        self.layout.addLayout(self.button_layout)

        # Save button
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_image)
        self.button_layout.addWidget(self.save_button)

        # Color button
        self.color_button = QPushButton("Choose Color")
        self.color_button.clicked.connect(self.choose_color)
        self.button_layout.addWidget(self.color_button)

        #set default mode to line
        self.mode="line"

        # test button
        self.spray_button = QPushButton("Brushes")
        self.spray_button.clicked.connect(self.spray)
        self.button_layout.addWidget(self.spray_button)

        # Initial canvas size
        self.canvas_width = 1920
        self.canvas_height = 1080
        self.pixmap = QPixmap(self.canvas_width, self.canvas_height)
        self.pixmap.fill(Qt.GlobalColor.white)
        self.canvas.setPixmap(self.pixmap)

        # Drawing state
        self.drawing = False
        self.last_point = QPoint()
        self.pen_color = QColor(Qt.GlobalColor.black)

        # Start listening for incoming data
        threading.Thread(target=self.receive_data, daemon=True).start()

    # def resizeEvent(self, event):
    #     """Adjust the canvas size according to the window size, excluding the buttons."""
    #     # Update canvas size dynamically based on window size minus the button layout area
    #     new_width = self.width()
    #     new_height = self.height() - self.button_layout.sizeHint().height()
    #
    #     if new_width != self.canvas_width or new_height != self.canvas_height:
    #         self.canvas_width = new_width
    #         self.canvas_height = new_height
    #
    #         # Create a new pixmap with the new size
    #         self.pixmap = QPixmap(self.canvas_width, self.canvas_height)
    #         self.pixmap.fill(Qt.GlobalColor.white)
    #
    #         # Redraw the previous content (scaled)
    #         painter = QPainter(self.pixmap)
    #         painter.drawPixmap(0,0, self.canvas.pixmap().scaled(self.canvas_width, self.canvas_height, Qt.AspectRatioMode.KeepAspectRatio))
    #         painter.end()
    #
    #         # Update the canvas with the new pixmap
    #         self.canvas.setPixmap(self.pixmap)
    #
    #     super().resizeEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            self.last_point = event.position()

    def mouseMoveEvent(self, event):
        if self.drawing and event.buttons() == Qt.MouseButton.LeftButton:
            current_point = (event.position())

            if self.mode == "line":
                # Draw on the local canvas
                self.draw_line(self.last_point, current_point, self.pen_color)

            elif self.mode == "spray":
                self.draw_spray(event)


            # Send drawing data to the server (scaled)
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

    #change mode to spray
    def spray(self):
        self.mode = "spray"

    def draw_spray(self, e):

        painter = QPainter(self.pixmap)
        p = painter.pen()
        p.setWidth(1)
        p.setColor(self.pen_color)
        painter.setPen(p)

        for n in range(SPRAY_PARTICLES):
            xo = random.gauss(0, SPRAY_DIAMETER)
            yo = random.gauss(0, SPRAY_DIAMETER)
            painter.drawPoint(
                int(e.position().x() + xo),
                int(e.position().y() + yo)
            )

        painter.end()
        self.canvas.setPixmap(self.pixmap)


    def draw_line(self, start, end, color):
        """Draw a line on the local canvas."""
        painter = QPainter(self.pixmap)
        pen = QPen(color, 5, Qt.PenStyle.DashLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        pen.setDashPattern([1,10])
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

    def get_scaled_point(self, point):
        """Scale the point to fit the canvas size after window resize."""
        scale_x = self.canvas.width() / self.width()
        scale_y = self.canvas.height() / self.height()
        return QPoint(int(point.x() * scale_x), int(point.y() * scale_y))





if __name__ == "__main__":
    app = QApplication(sys.argv)
    client = WhiteboardClient()
    client.show()
    sys.exit(app.exec())
