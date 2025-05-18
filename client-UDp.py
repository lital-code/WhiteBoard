import json
import struct
import sys
import socket
import threading
import uuid
from datetime import datetime

from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QByteArray, QBuffer, QIODevice
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QImage
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget, QFileDialog, \
    QColorDialog, QHBoxLayout, QDialog, QSlider, QRadioButton, QGridLayout, QButtonGroup, QCheckBox
import random

from BoardsDialog import BoardsDialog
from BrushSettingsDialog import BrushSettingsDialog


class WhiteboardClient(QMainWindow):

    new_drawing_signal = pyqtSignal(dict)  # Signal to pass drawing data to the main thread
    update_board_signal = pyqtSignal(dict)

    brush_settings = dict()

    #define a unique id for each client
    CLIENT_ID = str(uuid.uuid4())[:8]

    def __init__(self, server_host="127.0.0.1",multicast_group = "224.1.1.1", multicast_group_port=4000,drawing_port=4001,secondary_port = 4002):
        super().__init__()

        self.server_host = server_host
        self.drawing_port = drawing_port
        #default brush settings
        self.brush_settings = {"mode":"line", "opacity": 100, "diameter": 10, "density": 100, "width": 5,
                               "line_style": Qt.PenStyle.SolidLine, "cap_type": Qt.PenCapStyle.RoundCap,
                               "color":QColor(Qt.GlobalColor.black)}

        #initializing the UI
        self.setWindowTitle("Whiteboard Client")
        self.setMinimumSize(800, 600)

        #central widget and main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        #main canvas and pixmap
        self.canvas = QLabel()
        self.canvas.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.layout.addWidget(self.canvas)
        canvas_width = 1920
        canvas_height = 1080
        self.pixmap = QPixmap(canvas_width, canvas_height)
        self.pixmap.fill(Qt.GlobalColor.white)
        self.canvas.setPixmap(self.pixmap)

        #buttons layout
        self.button_layout = QHBoxLayout()
        self.layout.addLayout(self.button_layout)

        #boards button
        self.boards_button = QPushButton("My boards")
        self.boards_button.clicked.connect(self.open_boards_dialog)
        self.button_layout.addWidget(self.boards_button)

        # save button
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_image)
        self.button_layout.addWidget(self.save_button)

        # color button
        self.color_button = QPushButton("Choose Color")
        self.color_button.clicked.connect(self.choose_color)
        self.button_layout.addWidget(self.color_button)

        # brushes button
        self.brushes_button = QPushButton("Brushes")
        self.brushes_button.clicked.connect(self.open_brushes_dialog)
        self.button_layout.addWidget(self.brushes_button)


        #drawing state
        self.drawing = False
        self.last_point = QPoint()

        # Start listening for incoming data
        self.update_board_signal.connect(self.update_current_board)


        #connect to server
        try:
            #create the drawing socket and connect to the multicast group
            self.drawing_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.drawing_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.drawing_socket.bind(('', multicast_group_port))
            mreq = struct.pack("4sl", socket.inet_aton(multicast_group), socket.INADDR_ANY)
            self.drawing_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

            #create the secondary socket which will send peripheral data to the server (such as files, brush settings,etc.)
            self.secondary_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.secondary_socket.connect((server_host, secondary_port))

            #start the drawing thread
            threading.Thread(target=self.receive_drawing_data, daemon=True).start()

            ####### need to solve receiving brush settings from server without interfering with the Boards dialog reading data####

        except Exception as e:
            print(f"error connecting to servers: {e}")

    def update_current_board(self,new_pixmap):
        """update the pixmap"""
        self.pixmap = new_pixmap.get("original_resolution",QPixmap(1920,1080))
        self.canvas.setPixmap(self.pixmap)

    def update_drawing(self, data):
        """Handle received drawing data from the server into my canvas."""

        #get the coordinates to draw
        x1 = int(data.get("last_point_x",0))
        y1 = int(data.get("last_point_y",0))
        x2 = int(data.get("current_point_x",0))
        y2 = int(data.get("current_point_y",0))

        #create the QPoints to draw
        start_point = QPoint(x1, y1)
        end_point = QPoint(x2, y2)

        brush_settings = data["brush_settings"]
        self.reformat_brush_settings_to_qt(brush_settings)

        #draw based on the current brush mode
        if brush_settings.get("mode","")=="spray":
            self.draw_spray(start_point,brush_settings)
        elif brush_settings.get("mode","")=="line":
            self.draw_line(start_point, end_point, brush_settings)
        elif brush_settings.get("mode","")=="eraser":
            self.draw_eraser(start_point, end_point)

    def receive_drawing_data(self):
        """Receive drawing data from the server."""
        while True:
            try:
                data,addr = self.drawing_socket.recvfrom(1024)
                if data:
                    data = json.loads(data.decode())
                    print(f"data received from server: {data}")
                    if data.get("origin") != self.CLIENT_ID:
                        threading.Thread(target=self.update_drawing,args=(data,), daemon=True).start()

                        #self.update_drawing(data)
            except Exception as e:
                print(f"Error receiving data: {e}")


    def mousePressEvent(self, event):
        """change drawing state based on mouse press."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            self.last_point = event.position()

    def mouseMoveEvent(self, event):
        """draw on canvas when mouse is moved."""
        if self.drawing and event.buttons() == Qt.MouseButton.LeftButton:
            current_point = event.position()

            #draw based on the current brush mode
            if self.brush_settings.get("mode","") == "line":
                self.draw_line(self.last_point, current_point,self.brush_settings)
            elif self.brush_settings.get("mode","") == "spray":
                self.draw_spray(self.last_point,self.brush_settings)
            elif self.brush_settings.get("mode","") == "eraser":
                self.draw_eraser(self.last_point,current_point)

            #send the drawing data to the server
            self.send_drawing_data(self.last_point,current_point)
            #set the next starting point
            self.last_point = current_point

    def send_drawing_data(self, last_point, current_point):
        """formats data and sends the drawing data to the server"""

        #create a copy of the current brush settings
        brush_settings = self.brush_settings.copy()
        #format the brush settings to strings and ints
        brush_settings.update({"line_style": "dash" if self.brush_settings["line_style"] == Qt.PenStyle.DashLine else "solid",
                                  "cap_type": "square" if self.brush_settings["cap_type"] == Qt.PenCapStyle.SquareCap else "round",
                                  "color":self.brush_settings["color"].rgb()})

        # format data before sending to server
        data = {
            "origin": self.CLIENT_ID,
            "last_point_x": last_point.x(),
            "last_point_y": last_point.y(),
            "current_point_x": current_point.x(),
            "current_point_y": current_point.y(),
            "brush_settings": brush_settings,
        }

        try:
            # sending data to server
            self.drawing_socket.sendto(json.dumps(data).encode(), (self.server_host, self.drawing_port))
            print(f"sending data to server: {data}")
        except Exception as e:
            print(f"Error sending data: {e}")

    def mouseReleaseEvent(self, event):
        """change drawing state based on mouse release."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = False

    def save_image(self):
        """saving current pixmap as image."""
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Image", "", "PNG Files (*.png);;All Files (*)")
        if file_path:
            self.pixmap.save(file_path, "PNG")

    def choose_color(self):
        """opening color picker dialog"""
        color = QColorDialog.getColor(initial=self.brush_settings.get("color",QColor(Qt.GlobalColor.black)), parent=self, title="Select Pen Color")
        if color.isValid():
            #if the color is valid, update the brush settings with the color
            self.update_brush_settings(color=color)

    def update_brush_settings(self,**kwargs):
        """update the brush settings."""
        #settings the valid brush settings options
        valid_attrs = {"mode", "opacity", "diameter", "density", "width", "line_style", "cap_type", "color"}
        #iteraiting through the settings to update and updating them
        for attr, value in kwargs.items():
            if attr in valid_attrs:
                #update the new brush settings
                self.brush_settings.update({attr: value})
            else:
                print(f"Warning: '{attr}' is not a valid brush setting.")
        #send new brush settings to server
        print(f"Updated brush settings: {self.brush_settings}")

    def reformat_brush_settings_to_qt(self, brush_settings):
        """reformats brush settings from str to Qt."""
        #formating the color setting from int to QColor
        brush_settings.update({"color":QColor(brush_settings.get("color",Qt.GlobalColor.black))})
        #formating the line_style setting from string to Qt.PenStyle
        brush_settings.update({"line_style": Qt.PenStyle.SolidLine if brush_settings.get("line_style", "solid") == "solid" else Qt.PenStyle.DashLine})
        #formating the cap_type setting from string to Qt.PenCapStyle
        brush_settings.update({"cap_type": Qt.PenCapStyle.RoundCap if brush_settings.get("cap_type",
                                                                                         "round") == "round" else Qt.PenCapStyle.SquareCap})


    def draw_spray(self, last_point, brush_settings):
        """draw with spray brush"""
        painter = QPainter(self.pixmap)
        p = painter.pen()
        p.setWidth(1)
        p.setColor(brush_settings.get("color",QColor(Qt.GlobalColor.black)))
        painter.setPen(p)

        for n in range(brush_settings["density"]):
            xo = random.gauss(0, brush_settings["diameter"])
            yo = random.gauss(0, brush_settings["diameter"])
            painter.drawPoint(
                int(last_point.x() + xo),
                int(last_point.y() + yo)
            )

        painter.end()
        self.canvas.setPixmap(self.pixmap)

    def draw_line(self, start, end, brush_settings):
        """Draw a line on the canvas."""
        painter = QPainter(self.pixmap)
        alpha_color = brush_settings.get("color",QColor(Qt.GlobalColor.black))
        alpha_color.setAlphaF(brush_settings["opacity"]/100)
        pen = QPen(alpha_color, brush_settings.get("width"), brush_settings.get("line_style"), brush_settings.get("cap_type"), Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(start, end)
        painter.end()
        self.canvas.setPixmap(self.pixmap)

    def open_brushes_dialog(self):
        """open the brush settings dialog"""
        dlg = BrushSettingsDialog(self.brush_settings)
        dlg.update_brush_settings_sgnl.connect(self.brush_event_handle)
        dlg.exec()

    def brush_event_handle(self, event):
        """handle the return value of the brush settings dialog"""
        self.update_brush_settings(**event)

    def open_boards_dialog(self):
        """open the boards dialog"""
        boards_dialog = BoardsDialog(self.pixmap.toImage(),self.secondary_socket,self.update_board_signal)
        boards_dialog.exec()

    def draw_eraser(self, start, end):
        """Draw erasing line on the canvas."""
        painter = QPainter(self.pixmap)
        alpha_color =  QColor(Qt.GlobalColor.white)
        pen = QPen(alpha_color, 40, Qt.PenStyle.SolidLine,
                   Qt.PenCapStyle.SquareCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(start, end)
        painter.end()
        self.canvas.setPixmap(self.pixmap)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    client = WhiteboardClient("127.0.0.1")
    client.show()
    sys.exit(app.exec())