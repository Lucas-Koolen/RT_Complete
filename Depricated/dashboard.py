import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QTextEdit, QTabWidget, QGroupBox
)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import QTimer, Qt
import time

from logic.serial_comm import SerialCommunicator
from logic.db_connector import DatabaseConnector
from logic.rotation_logic import determine_rotation_sequence
from logic.height_sensor import parse_height_from_line
from logic.detector import CameraDetector
from config.config import *

class RotationDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rotation Table – Detection & Control")
        self.resize(1400, 900)

        # Modules
        self.serial = SerialCommunicator()
        self.db = DatabaseConnector()
        self.detector = CameraDetector()

        # Statusen
        self.latest_height = None
        self.latest_dimensions = None
        self.auto_mode = False

        # Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(200)

        # Layout
        self.tabs = QTabWidget()
        self.manual_tab = QWidget()
        self.auto_tab = QWidget()

        self.tabs.addTab(self.manual_tab, "Manual Control")
        self.tabs.addTab(self.auto_tab, "Auto Mode")

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)

        # Per tab invullen
        self.build_manual_tab()
        self.build_auto_tab()

    def build_manual_tab(self):
        layout = QVBoxLayout()

        control_box = QGroupBox("Sturing")
        controls = QHBoxLayout()
        self.forward_btn = QPushButton("Forwards")
        self.backward_btn = QPushButton("Backwards")
        self.stop_btn = QPushButton("Stop")
        controls.addWidget(self.forward_btn)
        controls.addWidget(self.backward_btn)
        controls.addWidget(self.stop_btn)
        control_box.setLayout(controls)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        layout.addWidget(control_box)
        layout.addWidget(QLabel("Live Log"))
        layout.addWidget(self.log_output)

        self.manual_tab.setLayout(layout)

        # Events koppelen
        self.forward_btn.clicked.connect(lambda: self.send_manual_command("SET 2 FWD"))
        self.backward_btn.clicked.connect(lambda: self.send_manual_command("SET 2 REV"))
        self.stop_btn.clicked.connect(lambda: self.send_manual_command("SET 2 STOP"))

    def build_auto_tab(self):
        layout = QVBoxLayout()

        self.auto_toggle = QPushButton("Start Auto Mode")
        self.auto_toggle.setCheckable(True)
        self.auto_toggle.clicked.connect(self.toggle_auto_mode)

        self.image_label = QLabel("Camera Feed komt hier")
        self.image_label.setFixedSize(800, 600)

        self.height_label = QLabel("Laatste hoogte: n.v.t.")
        self.match_result = QLabel("Matchresultaat: -")

        layout.addWidget(self.auto_toggle)
        layout.addWidget(self.image_label)
        layout.addWidget(self.height_label)
        layout.addWidget(self.match_result)

        self.auto_tab.setLayout(layout)
    
    def update_frame(self):
        # 1. Live camera detectie
        frame, dimensions = self.detector.get_frame()
        if frame is not None:
            self.latest_dimensions = dimensions
            image = QImage(frame.data, frame.shape[1], frame.shape[0], QImage.Format_RGB888)
            pix = QPixmap.fromImage(image).scaled(self.image_label.width(), self.image_label.height(), Qt.KeepAspectRatio)
            self.image_label.setPixmap(pix)

        # 2. Hoogte uitlezen
        line = self.serial.read_line()
        if line and line.startswith("HEIGHT:"):
            self.latest_height = parse_height_from_line(line)
            self.height_label.setText(f"Laatste hoogte: {self.latest_height} mm")

        # 3. Automatische modus actief
        if self.auto_mode and self.latest_dimensions and self.latest_height:
            l, b = self.latest_dimensions
            h = self.latest_height
            detected_box = {"length": l, "width": b, "height": h}

            match = self.db.find_best_match(l, b, h)
            if match:
                self.match_result.setText(f"Match: ID {match['commonId']}")
                sequence = determine_rotation_sequence(detected_box, match)
                for cmd in sequence:
                    self.serial.send_command(cmd)
                    self.log(f"⮞ {cmd}")
                    time.sleep(0.4)
                self.db.mark_as_placed(match['commonId'])
                self.auto_mode = False
                self.auto_toggle.setChecked(False)
                self.auto_toggle.setText("Start Auto Mode")
                self.log("✅ Doos verwerkt en gemarkeerd als geplaatst.")
            else:
                self.match_result.setText("Geen match gevonden.")
                self.log("⚠️ Geen match.")

    def toggle_auto_mode(self):
        self.auto_mode = self.auto_toggle.isChecked()
        if self.auto_mode:
            self.auto_toggle.setText("Auto Mode AAN (detectie actief)")
            self.log("▶ Automatische modus gestart.")
        else:
            self.auto_toggle.setText("Start Auto Mode")
            self.log("⏹ Automatische modus gestopt.")

    def send_manual_command(self, cmd):
        self.serial.send_command(cmd)
        self.log(f"[MANUAL] {cmd}")

    def log(self, message):
        self.log_output.append(message)

