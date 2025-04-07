import json
import sys
import socket
import threading
from datetime import datetime

from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QByteArray, QBuffer, QIODevice
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QImage
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget, QFileDialog, \
    QColorDialog, QHBoxLayout, QDialog, QSlider, QRadioButton, QGridLayout, QButtonGroup, QCheckBox
import random

from select import select


class clickableLabel(QLabel):
    board_clicked_sgnl = pyqtSignal(QLabel)
    def __init__(self):
        super().__init__()
        self.setProperty("active",False)

    def mousePressEvent(self, ev):
        self.setProperty("active",not self.property("active"))
        if self.property("active"):
            self.setStyleSheet("""
            QLabel{background-color:red}
            QLabel:hover{
                background-color:grey;
            }
            """)
        else:
            self.setStyleSheet("""
            QLabel{background-color:none}
            QLabel:hover{
                background-color:grey;
            }
            """)
        self.board_clicked_sgnl.emit(self)



class BoardsDialog(QDialog):
    def __init__(self,current_board,socket,update_board_signal):
        super().__init__()
        self.selected_board = None
        self.update_board_signal = update_board_signal
        self.socket = socket
        self.setWindowTitle("My Boards")
        self.setGeometry(200,200,800,600)
        self.setStyleSheet("""
            QLabel{
                max-width:192px;
                max-height:108px;
                padding:20px;
            }
            QLabel:hover{
                background-color:grey;
            }
            QLabel[active="True"]{
                background-color:red;
            }
            QGridLayout{
                background-color:black;
            }
        """)

        dialog_layout = QVBoxLayout()
        button_layout = QHBoxLayout()
        self.boards_layout = QGridLayout()
        self.boards = [{"original_resolution":QPixmap(current_board), "reduced_resolution":QPixmap(current_board.scaledToHeight(108)),"name":str(datetime.now()).replace(':', '')}]
        self.get_boards()
        self.populate_boards()


        upload_button = QPushButton()
        upload_button.setText("Upload")
        upload_button.clicked.connect(self.upload_board)

        open_button = QPushButton()
        open_button.setText("Open")
        open_button.clicked.connect(self.open_board)

        delete_button = QPushButton()
        delete_button.setText("Delete")
        delete_button.clicked.connect(self.delete_board)

        button_layout.addWidget(upload_button)
        button_layout.addWidget(open_button)
        button_layout.addWidget(delete_button)

        dialog_layout.addLayout(self.boards_layout)
        dialog_layout.addLayout(button_layout)
        self.setLayout(dialog_layout)

    def populate_boards(self):
        for index,board in enumerate(self.boards):
            label = clickableLabel()
            label.board_clicked_sgnl.connect(self.on_board_click)
            label.setPixmap(board["reduced_resolution"])
            label.setProperty("name",board["name"])
            self.boards_layout.addWidget(label)

    def upload_board(self):
        if self.selected_board:
            self.socket.send(json.dumps({"action":"save"}).encode())
            self.send_big_data(self.socket,self.pixmap_to_byte_array(self.selected_board["original_resolution"]))

    def open_board(self):
        if self.selected_board:
            self.update_board_signal.emit(self.selected_board)
            self.close()


    def delete_board(self):
        if self.selected_board and len(self.boards) > 1:
            self.socket.send(json.dumps({"action":"delete_board","data":self.selected_board["name"]}).encode())
            self.boards.remove(self.selected_board)
            self.selected_board = None
            # Remove all widgets from the grid layout
            for i in range(self.boards_layout.count()):
                item = self.boards_layout.itemAt(i)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
            self.populate_boards()

    def get_boards(self):
        self.socket.send(json.dumps({"action": "get_boards"}).encode())
        raw_data = self.socket.recv(1024)
        boards_amount = int(raw_data.decode())
        for i in range(boards_amount):
            file_name = self.socket.recv(1024).decode()
            self.socket.send(b"NAME_RECEIVED")
            board = self.byte_array_to_image(self.receive_big_data(self.socket))
            self.boards.append({"original_resolution":QPixmap(board),"reduced_resolution":QPixmap(board.scaledToHeight(108)),"name":file_name})

    def on_board_click(self,label):
        for i in range(self.boards_layout.count()):
            board = self.boards[i]
            item = self.boards_layout.itemAt(i).widget()
            if label:
                if label.property("name") == board["name"]:
                    self.selected_board = board
                else:
                    item.setProperty("active",False)
                    item.setStyleSheet("""
                                QLabel{background-color:none}
                                QLabel:hover{
                                    background-color:grey;
                                }
                                """)



    def receive_big_data(self, client_socket):
        data_size = int(client_socket.recv(1024).decode())
        client_socket.send(b"SIZE_RECEIVED")
        # data_name = data["data_name"]
        data = b''
        while data_size > 0:
            data += client_socket.recv(1024)
            data_size -= 1024
        return data

    def send_big_data(self, client_socket, data):
        data_size = len(data)  # Use len() for accurate size calculation, not sys.getsizeof
        print(f"sending big data to server file size: {data_size} data: {data}")

        # First send the size as a fixed-size 4-byte integer (standard method for sending data size)
        client_socket.sendall(data_size.to_bytes(4, byteorder='big'))

        # Then send the actual data
        client_socket.sendall(data)


    def pixmap_to_byte_array(self, pixmap):
        # Convert QPixmap to QByteArray
        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        pixmap.save(buffer, 'PNG')  # Save the pixmap as PNG format in the byte array
        return byte_array

    def image_to_byte_array(self,image:QImage):
        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(buffer, 'PNG')  # Save the pixmap as PNG format in the byte array
        return byte_array

    def byte_array_to_image(self, byte_array):
        # Convert byte array to QByteArray (if needed)
        image = QImage()
        image.loadFromData(byte_array)
        # if not image.loadFromData(byte_array):
        #     print("Error: Failed to load image from data")
        #     return None  # Or raise an exception if needed

        return image

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
        self.eraser = QRadioButton("eraser")
        brush_type_group.addButton(self.lineBrush)
        brush_type_group.addButton(self.spray_brush)
        brush_type_group.addButton(self.eraser)
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

        layout.addWidget(self.eraser,3,0,alignment=Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.submit_btn,4,1)

        self.setLayout(layout)

    def handle_submit(self):
        if self.eraser.isChecked():
            self.brush_settings = {"mode": "line",
                                   "opacity": 100, "diameter": self.spray_diameter.value(),
                                   "density": self.spray_density.value(), "width": 40,
                                   "dashed": Qt.PenStyle.SolidLine,
                                   "cap_type": Qt.PenCapStyle.SquareCap,
                                   "color":QColor(Qt.GlobalColor.white)}
        else:
            self.brush_settings = {"mode": "line" if self.lineBrush.isChecked() else "spray",
                               "opacity": self.opacity.value(), "diameter": self.spray_diameter.value(),
                               "density": self.spray_density.value(), "width": self.line_width.value(),
                               "dashed": Qt.PenStyle.DashLine if self.dash.isChecked() else Qt.PenStyle.SolidLine,
                               "cap_type": Qt.PenCapStyle.SquareCap if self.square_cap.isChecked() else Qt.PenCapStyle.RoundCap}
        self.brushes_signal.emit(self.brush_settings)
        self.close()




class WhiteboardClient(QMainWindow):
    new_drawing_signal = pyqtSignal(dict)  # Signal to pass drawing data to the main thread
    update_board_signal = pyqtSignal(dict)

    def __init__(self, host="127.0.0.1", port=5000):
        super().__init__()
        self.setWindowTitle("Whiteboard Client")
        self.setMinimumSize(800, 600)

        self.drawing_client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.drawing_client_socket.connect((host, port))
        self.drawing_client_socket.send(json.dumps({"connection_type":"drawing_info"}).encode())
        print("connected to drawing server")

        self.files_client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.files_client_socket.connect((host, port))
        self.files_client_socket.send(json.dumps({"connection_type": "files_info"}).encode())
        print("connected to files server")

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
        self.update_board_signal.connect(self.update_current_board)
        threading.Thread(target=self.receive_drawing_data, daemon=True).start()
        self.brush_settings = {"mode":"line", "opacity": 100, "diameter": 10, "density": 100, "width": 5,
                               "dashed": Qt.PenStyle.SolidLine, "cap_type": Qt.PenCapStyle.RoundCap}

    def update_current_board(self,board):
        self.pixmap = board["original_resolution"]
        self.canvas.setPixmap(self.pixmap)


    def update_drawing(self, data):
        """Handle received drawing data in the main thread."""
        x1 = int(data.get("last_point_x"))
        y1 = int(data.get("last_point_y"))
        x2 = int(data.get("current_point_x"))
        y2 = int(data.get("current_point_y"))
        color = data.get("pen_color")

        self.brush_settings = data.get("brush_settings")
        brush_type = self.brush_settings.get("mode")
        self.brush_settings.update({"dashed": Qt.PenStyle.DashLine if self.brush_settings["dashed"]=="dash" else Qt.PenStyle.SolidLine})
        self.brush_settings.update({"cap_type":Qt.PenCapStyle.SquareCap if self.brush_settings["cap_type"]=="square" else Qt.PenCapStyle.RoundCap})
        self.brush_settings.update({"color":QColor(self.brush_settings["color"])})
        start_point = QPoint(x1, y1)
        end_point = QPoint(x2, y2)
        if brush_type=="spray":
            self.draw_spray(start_point,end_point)
        else:
            self.draw_line(start_point, end_point, color)

    def receive_drawing_data(self):
        """Receive drawing data from the server."""
        while True:
            try:
                data = self.drawing_client_socket.recv(1024)
                if data:
                    data = json.loads(data.decode())
                    print(f"data received from server: {data}")
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
                self.draw_spray(self.last_point,current_point)

            data = {
                "last_point_x": self.last_point.x(),
                "last_point_y": self.last_point.y(),
                "current_point_x": current_point.x(),
                "current_point_y": current_point.y(),
                "pen_color": self.pen_color.rgb(),
                "brush_settings":{**self.brush_settings,
                                  "dashed": "dash" if self.brush_settings["dashed"] == Qt.PenStyle.DashLine else "solid",
                                  "cap_type": "square" if self.brush_settings["cap_type"] else "round",
                                  "color":self.brush_settings["color"].rgb() if "color" in self.brush_settings.keys() else ""
                                  }
            }

            try:
                self.drawing_client_socket.sendall(json.dumps(data).encode())
                print(f"sending data to server: {data}")
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

    def draw_spray(self, last_point,current_point):
        painter = QPainter(self.pixmap)
        p = painter.pen()
        p.setWidth(1)
        p.setColor(self.pen_color)
        painter.setPen(p)

        for n in range(self.brush_settings["density"]):
            xo = random.gauss(0, self.brush_settings["diameter"])
            yo = random.gauss(0, self.brush_settings["diameter"])
            painter.drawPoint(
                int(last_point.x() + xo),
                int(last_point.y() + yo)
            )

        painter.end()
        self.canvas.setPixmap(self.pixmap)

    def draw_line(self, start, end, color):
        """Draw a line on the local canvas."""
        painter = QPainter(self.pixmap)
        color = QColor(color)
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
        self.brush_settings:dict = event
        if "color" in self.brush_settings.keys():
            self.pen_color = self.brush_settings["color"]

    def open_boards_dialog(self):
        boards_dialog = BoardsDialog(self.pixmap.toImage(),self.files_client_socket,self.update_board_signal)
        boards_dialog.exec()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    client = WhiteboardClient()
    client.show()
    sys.exit(app.exec())
