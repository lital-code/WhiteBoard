import sys
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget, QFileDialog, \
    QColorDialog


class DrawingApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Drawing App")
        self.setGeometry(100, 100, 800, 600)

        # Central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Layout
        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        # Canvas setup
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

        # Variables for drawing
        self.drawing = False
        self.last_point = QPoint()
        self.pen_color = QColor(Qt.GlobalColor.black)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            self.last_point = event.position().toPoint()

    def mouseMoveEvent(self, event):
        if self.drawing and event.buttons() == Qt.MouseButton.LeftButton:
            painter = QPainter(self.pixmap)
            pen = QPen(self.pen_color, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawLine(self.last_point, event.position().toPoint())
            painter.end()
            self.last_point = event.position().toPoint()
            self.canvas.setPixmap(self.pixmap)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = False

    def save_image(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Image", "", "PNG Files (*.png);;All Files (*)",
                                                   options=options)
        if file_path:
            self.pixmap.save(file_path, "PNG")

    def choose_color(self):
        color = QColorDialog.getColor(initial=self.pen_color, parent=self, title="Select Pen Color")
        if color.isValid():
            self.pen_color = color


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DrawingApp()
    window.show()
    sys.exit(app.exec())
