import cv2

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QTextEdit,
    QGroupBox,
    QDialog,
    QTabWidget,
)

from logic.shapeDetector import detect_dimensions
from config.config import SERIAL_PORT, BAUD_RATE

from interfaces.dbConnector import DatabaseConnector
from interfaces.serialCommunicator import SerialCommunicator

from logic.movementLogic import MovementLogic

from interfaces.cameraInterface import get_frame

# ------------------------------------------------------------------------------
# 1) First dashboard: “AVØA Realtime Dashboard”
# ------------------------------------------------------------------------------

class RealtimeDashboard(QWidget):
    def __init__(self, cam, communicator: SerialCommunicator):
        super().__init__()

        self.cam = cam
        self.communicator = communicator
        self.movement_logic = MovementLogic(communicator)

        self.setWindowTitle("AVØA Realtime Dashboard")
        self.setGeometry(100, 100, 1920, 1080)
        self.setStyleSheet("background-color: #2f2f2f; color: white; font-size: 18px;")
        self.running = True

        # ─── Widgets ───────────────────────────────────────────────────────────────

        # QLabel for displaying the camera feed
        self.image_label = QLabel()
        self.image_label.setFixedSize(960, 720)
        self.image_label.setStyleSheet(
            "border: 2px solid gray; background-color: black;"
        )

        # Labels for length × breadth × height, match status, debug log
        self.lbh_label = QLabel("L × B × H: - × - × - mm")
        self.lbh_label.setStyleSheet("background-color: #cc3333; padding: 10px;")

        self.match_label = QLabel("Match: -")
        self.match_label.setStyleSheet("background-color: #cc3333; padding: 10px;")

        self.debug_label = QLabel("🪵 Debug: geen activiteit")
        self.debug_label.setStyleSheet("padding: 10px; color: #888888;")

        # ─── Layout ────────────────────────────────────────────────────────────────

        left_panel = QVBoxLayout()
        left_panel.addWidget(self.lbh_label)
        left_panel.addWidget(self.match_label)
        left_panel.addWidget(self.debug_label)
        left_panel.addStretch()

        right_panel = QVBoxLayout()
        right_panel.addWidget(QLabel("<b>LIVE CAM FEED</b>"))
        right_panel.addWidget(self.image_label)
        right_panel.addStretch()

        main_layout = QHBoxLayout()
        main_layout.addLayout(left_panel)
        main_layout.addLayout(right_panel)

        self.setLayout(main_layout)

        # (Optional) If you plan to drive frames via a timer or external call:
        # self.frame_timer = QTimer()
        # self.frame_timer.timeout.connect(self.grab_and_update_frame)
        # self.frame_timer.start(30)  # e.g. ~30 FPS

        self.dataBase = DatabaseConnector()

        self.frame_timer = QTimer(self)
        
        self.frame_timer.setSingleShot(True)
        self.frame_timer.timeout.connect(self.update_frame)
        self.frame_timer.start(100)  # Kick off the first frame


    def update_frame(self):
        """
        Call this method whenever you have a new OpenCV frame to display.
        Assumes detect_dimensions(frame) returns:
          length, width, height, matched_id, match_ok, log, frame_with_overlay
        """

        if(self.cam is None):
            print("❌ Camera is not initialized.")
            self.frame_timer.start(100)  # Restart timer to try again
            return

        frame = get_frame(self.cam)

        if frame is None:
            print("⚠️ Geen frame ontvangen, probeer opnieuw.")
            self.frame_timer.start(100)
            return

        # ─── Dimension detection; overlay, etc. ─────────────────────────────────
        length, width, height, centerX, centerY, angle, shape, matched_id, match_ok, log, frame_with_overlay = detect_dimensions(frame, self.dataBase, self.communicator)

        self.movement_logic.handle_movement(angle, centerX, centerY, width, length, height)

        #print(f"Detected object with center at ({centerX}, {centerY})")

        # ─── Convert to QImage + QPixmap ────────────────────────────────────────
        img_rgb = cv2.cvtColor(frame_with_overlay, cv2.COLOR_BGR2RGB)
        h, w, ch = img_rgb.shape
        bytes_per_line = ch * w
        qt_image = QImage(
            img_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888
        )
        pixmap = (
            QPixmap.fromImage(qt_image)
            .scaled(
                self.image_label.width(),
                self.image_label.height(),
                Qt.KeepAspectRatio,
            )
        )
        self.image_label.setPixmap(pixmap)

        # ─── Update all labels ───────────────────────────────────────────────────
        self.debug_label.setText(f"Debug: {log}")
        self.lbh_label.setText(
            f"L × B × H: {length:.1f} × {width:.1f} × {height:.1f} mm Shape: {shape.shapeToString()}"
        )
        # Change background based on match_ok
        if match_ok:
            self.lbh_label.setStyleSheet("background-color: #339933; padding: 10px;")
        else:
            self.lbh_label.setStyleSheet("background-color: #cc3333; padding: 10px;")

        if matched_id:
            self.match_label.setText(f"Match: {matched_id}")
            self.match_label.setStyleSheet("background-color: #339933; padding: 10px;")
        else:
            self.match_label.setText("Match: geen")
            self.match_label.setStyleSheet("background-color: #cc3333; padding: 10px;")

        self.frame_timer.start(100)


# ------------------------------------------------------------------------------
# 2) Second dashboard: “Manual Control Dashboard”
# ------------------------------------------------------------------------------

class ManualControlDashboard(QWidget):
    def __init__(self, communicator: SerialCommunicator):
        super().__init__()

        self.l2_position = None  # Tracks position of L2 (servo 4)
        self.setWindowTitle("Manual Control Dashboard")
        self.resize(1200, 900)
        self.setup_stylesheet()

        self.serialCommunicator = communicator

        self.active_buttons = {}
        self.auto_stop_timers = {}
        self.init_ui()
        self.show_safety_popup()

        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.updateUI)
        self.status_timer.start(200)

    def setup_stylesheet(self):
        self.setStyleSheet(
            """
            * { font-size: 14pt; font-family: Arial; }
            QWidget { background-color: #2b2b2b; color: #f0f0f0; }
            QPushButton {
                background-color: #3c3f41; border: 1px solid #555;
                border-radius: 6px; padding: 8px 16px; color: #ffffff;
            }
            QPushButton:hover { background-color: #ffaa40; color: #000000; }
            QPushButton:pressed, QPushButton[active="true"] {
                background-color: #ffaa00; color: #000000;
                font-size: 18pt; padding: 12px 24px;
            }
            QLineEdit, QTextEdit {
                background-color: #2b2b2b; color: #f0f0f0;
                border: 1px solid #555; border-radius: 6px; padding: 6px;
            }
            QLineEdit[echoMode="0"]::placeholder,
            QLineEdit::placeholder,
            QTextEdit::placeholder {
                color: #ffaa00;
            }
            QGroupBox {
                min-height: 80px; border: 1px solid #555; border-radius: 8px;
                background-color: #1e1e1e; margin-top: 10px; padding: 10px;
            }
            QGroupBox:title {
                subcontrol-origin: margin; subcontrol-position: top center;
                padding: 0 6px; color: #ffaa00; font-weight: bold;
            }
            QLabel {
                color: #dddddd; font-size: 14pt;
                padding: 6px; border-radius: 6px;
            }
            QLabel[active="true"] {
                background-color: #ffaa00; color: #000000;
            }
            """
        )

    def init_ui(self):
        layout = QVBoxLayout()

        # 1) Conveyor 1 & 2
        layout.addLayout(
            self.create_servo_row(
                [(1, "Conveyor 1"), (2, "Conveyor 2")], self.add_directional_controls
            )
        )

        # 2) Pusher 1 & 2
        layout.addLayout(
            self.create_servo_row(
                [(1, "Pusher 1"), (2, "Pusher 2")], self.add_pusher_controls
            )
        )

        # 3) Turntable 1 & 2
        layout.addLayout(
            self.create_servo_row(
                [(1, "Turntable 1"), (2, "Turntable 2")],
                self.add_rotation_controls,
            )
        )

        # 4) L1 (servo 3) & L2 (servo 4) fixed positions
        layout.addLayout(
            self.create_servo_row(
                [(1, "L1 (degrees)"), (2, "L2 (degrees)")],
                self.add_fixed_position_controls,
            )
        )

        # Sensor panel + log output
        layout.addWidget(self.build_sensor_panel())
        layout.addWidget(QLabel("Log:"))

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        self.setLayout(layout)

    def create_servo_row(self, servo_defs, control_func):
        row = QHBoxLayout()
        row.setSpacing(30)
        for servo_num, name in servo_defs:
            group = QGroupBox(f"{name} (Servo {servo_num})")
            group_layout = QVBoxLayout()
            group_layout.addLayout(control_func(servo_num))
            group.setLayout(group_layout)
            row.addWidget(group)
        return row

    def build_sensor_panel(self):
        self.sensor_group = QGroupBox("Sensors")
        self.sensor_layout = QHBoxLayout()

        # Left column: Beam sensors + limit switches
        left_column = QVBoxLayout()
        beam_group = QGroupBox("Beam Sensors")
        beam_layout = QHBoxLayout()
        self.beam1_label = QLabel("Beam Sensor 1: unknown")
        self.beam2_label = QLabel("Beam Sensor 2: unknown")
        beam_layout.addWidget(self.beam1_label)
        beam_layout.addWidget(self.beam2_label)
        beam_group.setLayout(beam_layout)

        limit_group = QGroupBox("Limit Switches")
        limit_layout = QHBoxLayout()
        self.limit1_label = QLabel("Limit Switch 1: unknown")
        self.limit2_label = QLabel("Limit Switch 2: unknown")
        limit_layout.addWidget(self.limit1_label)
        limit_layout.addWidget(self.limit2_label)
        limit_group.setLayout(limit_layout)

        left_column.addWidget(beam_group)
        left_column.addWidget(limit_group)

        # Right column: Height sensor
        right_column = QVBoxLayout()
        height_group = QGroupBox("Height Sensor")
        height_layout = QVBoxLayout()
        self.height_label = QLabel("Height: unknown")
        height_layout.addWidget(self.height_label)
        height_group.setLayout(height_layout)
        right_column.addWidget(height_group)

        self.sensor_layout.addLayout(left_column)
        self.sensor_layout.addLayout(right_column)
        self.sensor_group.setLayout(self.sensor_layout)
        return self.sensor_group

    def log(self, message):
        self.log_output.append(message)

    def show_safety_popup(self):
        popup = QDialog(self)
        popup.setWindowTitle("Safety Check")
        popup.setModal(True)
        popup.setStyleSheet(self.styleSheet())

        layout = QVBoxLayout()
        label = QLabel(
            "Are Flipper 1, Flipper 2, and Conveyor 1 clear?\nIf not, please clear the area."
        )
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        confirm_button = QPushButton("Confirm: area is clear")
        confirm_button.clicked.connect(lambda: self.perform_safety_sequence(popup))
        layout.addWidget(confirm_button)

        popup.setLayout(layout)
        popup.exec_()

    def perform_safety_sequence(self, popup):
        self.serialCommunicator.moveConveyor(2, "FWD")
        self.serialCommunicator.moveFlipper(1, "CLEAR")
        self.serialCommunicator.moveFlipper(2, "CLEAR")
        QTimer.singleShot(1000, lambda: self.serialCommunicator.moveConveyor(2, "STOP"))
        popup.accept()

    def add_directional_controls(self, servo):
        row = QHBoxLayout()
        self.active_buttons[servo] = []

        def handle_click(btn, direction):
            for b in self.active_buttons[servo]:
                b.setStyleSheet("")
            btn.setStyleSheet(
                "background-color: #ffaa00; color: black; font-size: 16pt; padding: 10px 20px;"
            )
            self.serialCommunicator.moveConveyor(servo, direction)

        for label, direction in [("Forewards", "FWD"), ("Backwards", "REV"), ("Stop", "STOP")]:
            btn = QPushButton(label)
            btn.clicked.connect(lambda _, b=btn, d=direction: handle_click(b, d))
            self.active_buttons[servo].append(btn)
            row.addWidget(btn)

        return row

    def add_rotation_controls(self, servo):
        row = QHBoxLayout()
        angle_input = QLineEdit()
        angle_input.setPlaceholderText("Graden (-360 tot 360)")
        angle_input.setStyleSheet("QLineEdit::placeholder { color: #ffcc80; }")

        btn_fwd = QPushButton("Turn FWD")
        btn_rev = QPushButton("Turn REV")

        def rotate(direction, btn):
            angle_text = angle_input.text()
            try:
                degrees = abs(int(angle_text))
            except ValueError:
                self.log("Ongeldige invoer voor graden.")
                return

            duration_ms = int((degrees / 360) * 1600)
            btn.setStyleSheet(
                "background-color: #ffaa00; color: black; font-size: 16pt; padding: 10px 20px;"
            )
            self.serialCommunicator.rotateRotator(servo, degrees, direction)

            if servo in [1, 7]:
                QTimer.singleShot(duration_ms, lambda: btn.setStyleSheet(""))
            else:
                btn.setStyleSheet("")

        btn_fwd.clicked.connect(lambda: rotate("FWD", btn_fwd))
        btn_rev.clicked.connect(lambda: rotate("REV", btn_rev))

        row.addWidget(angle_input)
        row.addWidget(btn_fwd)
        row.addWidget(btn_rev)
        return row

    def add_fixed_position_controls(self, servo):
        row = QHBoxLayout()
        self.active_buttons[servo] = []

        def handle_click(btn, position):
            for b in self.active_buttons[servo]:
                b.setStyleSheet("")
            btn.setStyleSheet("background-color: #ffaa00; color: black;")
            self.serialCommunicator.moveFlipper(servo, position)

        for label, position in [("Clear", "CLEAR"), ("Box Enter", "ENTER"), ("Box Out", "EXIT")]:
            btn = QPushButton(label)
            btn.clicked.connect(lambda _, b=btn, p=position: handle_click(b, p))
            self.active_buttons[servo].append(btn)
            row.addWidget(btn)

        return row

    def add_pusher_controls(self, servo):
        row = QHBoxLayout()
        time_input = QLineEdit()
        time_input.setPlaceholderText("mm voor Forwards (Push away)")
        time_input.setStyleSheet("QLineEdit::placeholder { color: #ffcc80; }")

        btn_fwd = QPushButton("Forwards (mm)")
        btn_rev = QPushButton("Backwards (auto-stop)")
        btn_stop = QPushButton("Stop")

        self.active_buttons[servo] = [btn_fwd, btn_rev]

        def handle_pusher_click(btn, direction, distance=None):

            for b in self.active_buttons[servo]:
                b.setStyleSheet("")
            btn.setStyleSheet("background-color: #ffaa00; color: black; font-size: 16pt; padding: 10px 20px;")
            
            self.serialCommunicator.movePusher(servo, direction, distance)

        btn_fwd.clicked.connect(lambda: handle_pusher_click(btn_fwd, "FWD", int(time_input.text()) if time_input.text().isdigit() else None))

        btn_rev.clicked.connect(lambda: handle_pusher_click(btn_rev, "REV"))

        btn_stop.clicked.connect(lambda: handle_pusher_click(btn_stop, "STOP"))	

        row.addWidget(time_input)
        row.addWidget(btn_fwd)
        row.addWidget(btn_rev)
        row.addWidget(btn_stop)

        if servo == 2:
            self.pusher2_buttons = [btn_fwd, btn_rev]

        return row

    def updateUI(self):
        # Get latest info from communicator class
        self.serialCommunicator.update_from_serial()

        if hasattr(self, "pusher2_buttons"):
            state = self.serialCommunicator.get_flipper2_pos() == 200
            for btn in self.pusher2_buttons:
                btn.setEnabled(state)
                if not state:
                    btn.setStyleSheet("background-color: #555555; color: #aaaaaa;")
                else:
                    btn.setStyleSheet("")
        
        if self.serialCommunicator.get_beam1_state():
            self.beam1_label.setText("Beam sensor 1: BROKEN")
            self.beam1_label.setProperty("active", True)
            self.beam1_label.setStyle(self.beam1_label.style())
        else:
            self.beam1_label.setText("Beam sensor 1: NOT BROKEN")
            self.beam1_label.setProperty("active", False)
            self.beam1_label.setStyle(self.beam1_label.style())

        if self.serialCommunicator.get_beam2_state():
            self.beam2_label.setText("Beam sensor 2: BROKEN")
            self.beam2_label.setProperty("active", True)
            self.beam2_label.setStyle(self.beam2_label.style())
        else:
            self.beam2_label.setText("Beam sensor 2: NOT BROKEN")
            self.beam2_label.setProperty("active", False)
            self.beam2_label.setStyle(self.beam2_label.style())

        if self.serialCommunicator.get_limit1_state():
            self.limit1_label.setText("Limit switch 1: PRESSED")
            self.limit1_label.setProperty("active", True)
            self.limit1_label.setStyle(self.limit1_label.style())
        else:
            self.limit1_label.setText("Limit switch 1: NOT PRESSED")
            self.limit1_label.setProperty("active", False)
            self.limit1_label.setStyle(self.limit1_label.style())
        
        if self.serialCommunicator.get_limit2_state():
            self.limit2_label.setText("Limit switch 2: PRESSED")
            self.limit2_label.setProperty("active", True)
            self.limit2_label.setStyle(self.limit2_label.style())
        else:
            self.limit2_label.setText("Limit switch 2: NOT PRESSED")
            self.limit2_label.setProperty("active", False)
            self.limit2_label.setStyle(self.limit2_label.style())

        if self.serialCommunicator.get_height() is not None:
            height = self.serialCommunicator.get_height()
            self.height_label.setText(f"Height: {height} mm")
            self.height_label.setProperty("active", True)
            self.height_label.setStyle(self.height_label.style())
        else:
            self.height_label.setText("Height: NULL")
            self.height_label.setProperty("active", False)
            self.height_label.setStyle(self.height_label.style())

# ------------------------------------------------------------------------------
# 3) Main application: combine both dashboards into a QTabWidget
# ------------------------------------------------------------------------------

class MainDashboard(QTabWidget):
    def __init__(self, cam, communicator: SerialCommunicator):
        super().__init__()
        self.setWindowTitle("Combined Dashboard")
        self.resize(1600, 1000)

        # Create instances of each dashboard
        self.realtime_tab = RealtimeDashboard(cam, communicator)
        self.manual_tab = ManualControlDashboard(communicator)

        # Add them as tabs
        self.addTab(self.realtime_tab, "Realtime")
        self.addTab(self.manual_tab, "Manual Control")
