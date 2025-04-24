from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QDialog, QGridLayout, QLabel, QButtonGroup, QRadioButton, QSlider, QCheckBox, QVBoxLayout, \
    QPushButton

class BrushSettingsDialog(QDialog):

    #update brush settings signal
    update_brush_settings_sgnl = pyqtSignal(dict)

    def __init__(self,brush_settings):
        super().__init__()

        #initialize the UI
        self.setWindowTitle("Brushes")

        layout = QGridLayout()
        message = QLabel("Choose your brush type:")
        self.brush_type_group = QButtonGroup(self)
        self.lineBrush = QRadioButton("line")
        self.spray_brush = QRadioButton("spray")
        self.eraser = QRadioButton("eraser")
        self.brush_type_group.addButton(self.lineBrush)
        self.brush_type_group.addButton(self.spray_brush)
        self.brush_type_group.addButton(self.eraser)
        match brush_settings.get("mode"):
            case "line":
                self.lineBrush.setChecked(True)
            case "spray":
                self.spray_brush.setChecked(True)
            case "eraser":
                self.eraser.setChecked(True)

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
        self.dash.setChecked(True) if brush_settings.get("line_style","solid") == Qt.PenStyle.DashLine else self.dash.setChecked(False)

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
        brush_settings = {"mode": self.brush_type_group.checkedButton().text(),
                               "opacity": self.opacity.value(), "diameter": self.spray_diameter.value(),
                           "density": self.spray_density.value(), "width": self.line_width.value(),
                           "line_style": Qt.PenStyle.DashLine if self.dash.isChecked() else Qt.PenStyle.SolidLine,
                           "cap_type": Qt.PenCapStyle.SquareCap if self.square_cap.isChecked() else Qt.PenCapStyle.RoundCap}

        self.update_brush_settings_sgnl.emit(brush_settings)
        self.close()