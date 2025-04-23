import json
from datetime import datetime

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QDialog, QGridLayout
from Tools import pixmap_to_byte_array, send_big_data, byte_array_to_image, receive_big_data


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
            send_big_data(self.socket,pixmap_to_byte_array(self.selected_board["original_resolution"]))

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
            board = byte_array_to_image(receive_big_data(self.socket))
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