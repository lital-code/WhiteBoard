import json
import sys
import socket
import threading
from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget, QFileDialog, QColorDialog, QHBoxLayout, QDialog, QDialogButtonBox, QRadioButton, QGridLayout
import random

SPRAY_PARTICLES = 100
SPRAY_DIAMETER = 10

class CustomDialog(QDialog):
    brushes_signal = pyqtSignal(str)

    def __init__(self, mode):
        super().__init__()
        self.setWindowTitle("Brushes")
        self.mode = mode

        layout = QGridLayout()
        message = QLabel("Choose your brush type:")
        self.lineBrush = QRadioButton("solid line")
        self.lineBrush.toggled.connect(self.brush_type_handle)
        self.spray_brush = QRadioButton("spray")
        self.spray_brush.toggled.connect(self.brush_type_handle)

        if self.mode == "line":
            self.lineBrush.toggle()
        elif self.mode == "spray":
            self.spray_brush.toggle()

        layout.addWidget(message)
        layout.addWidget(self.lineBrush)
        layout.addWidget(self.spray_brush)

        self.setLayout(layout)

    def brush_type_handle(self):
        if self.lineBrush.isChecked():
            self.mode = "line"
        elif self.spray_brush.isChecked():
            self.mode = "spray"

    def closeEvent(self, a0):
        self.brushes_signal.emit(self.mode)


class WhiteboardClient(QMainWindow):
    new_drawing_signal = pyqtSignal(dict)  # Signal to pass drawing data to the main thread

    def __init__(self, host="127.0.0.1", port=12345):
        super().__init__()
        self.setWindowTitle("Whiteboard Client")
        self.setMinimumSize(800, 600)

        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((host, port))

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        self.canvas = QLabel()
        self.canvas.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.layout.addWidget(self.canvas)

        self.button_layout = QHBoxLayout()
        self.layout.addLayout(self.button_layout)

        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_image)
        self.button_layout.addWidget(self.save_button)

        self.color_button = QPushButton("Choose Color")
        self.color_button.clicked.connect(self.choose_color)
        self.button_layout.addWidget(self.color_button)

        self.mode = "line"
        self.brushes_button = QPushButton("Brushes")
        self.brushes_button.clicked.connect(self.open_brushes_dialog)
        self.button_layout.addWidget(self.brushes_button)

        self.canvas_width = 1920
        self.canvas_height = 1080
        self.pixmap = QPixmap(self.canvas_width, self.canvas_height)
        self.pixmap.fill(Qt.GlobalColor.white)
        self.canvas.setPixmap(self.pixmap)

        self.drawing = False
        self.last_point = QPoint()
        self.pen_color = QColor(Qt.GlobalColor.black)

        # Start listening for incoming data
        self.new_drawing_signal.connect(self.update_drawing)
        threading.Thread(target=self.receive_data, daemon=True).start()

    def update_drawing(self, data):
        """Handle received drawing data in the main thread."""
        x1 = data.get("last_point_x")
        y1 = data.get("last_point_y")
        x2 = data.get("current_point_x")
        y2 = data.get("current_point_y")
        color = data.get("pen_color")

        start_point = QPoint(x1, y1)
        end_point = QPoint(x2, y2)
        self.draw_line(start_point, end_point, color)

    def receive_data(self):
        """Receive drawing data from the server."""
        while True:
            try:
                data = self.client_socket.recv(1024)
                if data:
                    data = json.loads(data.decode())
                    self.new_drawing_signal.emit(data)  # Emit signal to update drawing
            except Exception as e:
                print(f"Error receiving data: {e}")
                break

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            self.last_point = event.position()

    def mouseMoveEvent(self, event):
        if self.drawing and event.buttons() == Qt.MouseButton.LeftButton:
            current_point = event.position()

            if self.mode == "line":
                self.draw_line(self.last_point, current_point, self.pen_color)

            elif self.mode == "spray":
                self.draw_spray(event)

            data = {
                "last_point_x": self.last_point.x(),
                "last_point_y": self.last_point.y(),
                "current_point_x": current_point.x(),
                "current_point_y": current_point.y(),
                "pen_color": self.pen_color.rgb()
            }

            try:
                self.client_socket.sendall(json.dumps(data).encode())
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
        pen = QPen(color, 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(start, end)
        painter.end()
        self.canvas.setPixmap(self.pixmap)

    def open_brushes_dialog(self):
        dlg = CustomDialog(self.mode)
        dlg.brushes_signal.connect(self.brush_event_handle)
        dlg.exec()

    def brush_event_handle(self, event):
        self.mode = event


if __name__ == "__main__":
    app = QApplication(sys.argv)
    client = WhiteboardClient()
    client.show()
    sys.exit(app.exec())
