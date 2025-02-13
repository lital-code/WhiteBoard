import json
import sys
import socket
import threading
from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget, QFileDialog, \
    QColorDialog, QHBoxLayout, QDialog, QSlider, QRadioButton, QGridLayout, QButtonGroup, QCheckBox
import random

class BoardsDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("My Boards")

class CustomDialog(QDialog):
    brushes_signal = pyqtSignal(dict)

    def __init__(self,brush_settings):
        super().__init__()
        self.setWindowTitle("Brushes")

        layout = QGridLayout()
        message = QLabel("Choose your brush type:")
        brush_type_group = QButtonGroup(self)
        self.lineBrush = QRadioButton("line")
        self.spray_brush = QRadioButton("spray")
        brush_type_group.addButton(self.lineBrush)
        brush_type_group.addButton((self.spray_brush))
        self.spray_brush.setChecked(True) if brush_settings["mode"]=="spray" else self.lineBrush.setChecked(True)

        self.line_brush_group = QButtonGroup(self)
        self.round_cap = QRadioButton("Round Cap")
        self.square_cap = QRadioButton("Square Cap")
        self.round_cap.setChecked(True) if brush_settings["cap_type"]==Qt.PenCapStyle.RoundCap else self.square_cap.setChecked(True)
        self.line_brush_group.addButton(self.round_cap)
        self.line_brush_group.addButton(self.square_cap)
        self.line_width = QSlider(Qt.Orientation.Horizontal)
        self.line_width.setRange(5,50)
        self.line_width.setPageStep(1)
        self.line_width.setValue(brush_settings["width"])
        self.opacity = QSlider(Qt.Orientation.Horizontal)
        self.opacity.setRange(0,100)
        self.opacity.setValue(brush_settings["opacity"])
        self.opacity.setPageStep(10)
        self.dash = QCheckBox("dashed")
        self.dash.setChecked(True) if brush_settings["dashed"] == Qt.PenStyle.DashLine else self.dash.setChecked(False)

        self.spray_diameter = QSlider(Qt.Orientation.Horizontal)
        self.spray_diameter.setRange(5,50)
        self.spray_diameter.setValue(brush_settings["diameter"])
        self.spray_density = QSlider(Qt.Orientation.Horizontal)
        self.spray_density.setRange(50,500)
        self.spray_density.setValue(brush_settings["density"])

        line_layout = QVBoxLayout()
        line_layout.addWidget(self.round_cap)
        line_layout.addWidget(self.square_cap)
        line_layout.addWidget(QLabel("width"))
        line_layout.addWidget(self.line_width)
        line_layout.addWidget(QLabel("opacity"))
        line_layout.addWidget(self.opacity)
        line_layout.addWidget(self.dash)

        spray_layout = QVBoxLayout()
        spray_layout.addWidget(QLabel("diameter"))
        spray_layout.addWidget(self.spray_diameter)
        spray_layout.addWidget(QLabel("density"))
        spray_layout.addWidget(self.spray_density)

        self.submit_btn = QPushButton()
        self.submit_btn.setText("OK")
        self.submit_btn.clicked.connect(self.handle_submit)

        layout.addWidget(message,0,0)
        layout.addWidget(self.lineBrush,1,0,alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(line_layout,1,1)
        layout.addWidget(self.spray_brush,2,0,alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(spray_layout,2,1)

        layout.addWidget(self.submit_btn,3,1)

        self.setLayout(layout)

    def handle_submit(self):
        self.brush_settings = {"mode": "line" if self.lineBrush.isChecked() else "spray",
                               "opacity": self.opacity.value(), "diameter": self.spray_diameter.value(),
                               "density": self.spray_density.value(), "width": self.line_width.value(),
                               "dashed": Qt.PenStyle.DashLine if self.dash.isChecked() else Qt.PenStyle.SolidLine,
                               "cap_type": Qt.PenCapStyle.SquareCap if self.square_cap.isChecked() else Qt.PenCapStyle.RoundCap}
        self.brushes_signal.emit(self.brush_settings)
        self.close()




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

        self.boards_button = QPushButton("My boards")
        self.boards_button.clicked.connect(self.open_boards_dialog)
        self.button_layout.addWidget(self.boards_button)

        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_image)
        self.button_layout.addWidget(self.save_button)

        self.color_button = QPushButton("Choose Color")
        self.color_button.clicked.connect(self.choose_color)
        self.button_layout.addWidget(self.color_button)

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
        self.brush_settings = {"mode":"line", "opacity": 100, "diameter": 10, "density": 100, "width": 5,
                               "dashed": Qt.PenStyle.SolidLine, "cap_type": Qt.PenCapStyle.RoundCap}

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

            if self.brush_settings["mode"] == "line":
                self.draw_line(self.last_point, current_point, self.pen_color)

            elif self.brush_settings["mode"] == "spray":
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
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Image", "", "PNG Files (*.png);;All Files (*)")
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

        for n in range(self.brush_settings["density"]):
            xo = random.gauss(0, self.brush_settings["diameter"])
            yo = random.gauss(0, self.brush_settings["diameter"])
            painter.drawPoint(
                int(e.position().x() + xo),
                int(e.position().y() + yo)
            )

        painter.end()
        self.canvas.setPixmap(self.pixmap)

    def draw_line(self, start, end, color):
        """Draw a line on the local canvas."""
        painter = QPainter(self.pixmap)
        color.setAlphaF(self.brush_settings["opacity"]/100)
        pen = QPen(color, self.brush_settings["width"], self.brush_settings["dashed"], self.brush_settings["cap_type"], Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(start, end)
        painter.end()
        self.canvas.setPixmap(self.pixmap)

    def open_brushes_dialog(self):
        dlg = CustomDialog(self.brush_settings)
        dlg.brushes_signal.connect(self.brush_event_handle)
        dlg.exec()

    def brush_event_handle(self, event):
        self.brush_settings = event

    def open_boards_dialog(self):
        boards_dialog = BoardsDialog()
        boards_dialog.exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    client = WhiteboardClient()
    client.show()
    sys.exit(app.exec())
