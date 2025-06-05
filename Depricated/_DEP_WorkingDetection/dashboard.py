import sys
import cv2
import numpy as np
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout, QHBoxLayout

from logic.detection import detect_dimensions
from sensor.height_sensor import start_sensor_thread
from logic import camera_module

class LiveFeedDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AVØA Realtime Dashboard")
        self.setGeometry(100, 100, 1920, 1080)
        self.setStyleSheet("background-color: #2f2f2f; color: white; font-size: 18px;")
        self.running = True

        self.image_label = QLabel()
        self.image_label.setFixedSize(960, 720)
        self.image_label.setStyleSheet("border: 2px solid gray; background-color: black;")

        self.lbh_label = QLabel("L × B × H: - × - × - mm")
        self.lbh_label.setStyleSheet("background-color: #cc3333; padding: 10px;")

        self.match_label = QLabel("Match: -")
        self.match_label.setStyleSheet("background-color: #cc3333; padding: 10px;")

        self.debug_label = QLabel("🪵 Debug: geen activiteit")
        self.debug_label.setStyleSheet("padding: 10px; color: #888888;")

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

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            print("⛔ ESC gedrukt — netjes afsluiten")
            self.running = False
            QApplication.quit()

    def update_frame(self, frame):
        length, width, height, matched_id, match_ok, log, frame_with_overlay = detect_dimensions(frame)

        img_rgb = cv2.cvtColor(frame_with_overlay, cv2.COLOR_BGR2RGB)
        h, w, ch = img_rgb.shape
        bytes_per_line = ch * w
        qt_image = QImage(img_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image).scaled(self.image_label.width(), self.image_label.height(), Qt.KeepAspectRatio)
        self.image_label.setPixmap(pixmap)

        self.debug_label.setText(f"Debug: {log}")
        self.lbh_label.setText(f"L × B × H: {length:.1f} × {width:.1f} × {height:.1f} mm")
        self.lbh_label.setStyleSheet("background-color: #339933; padding: 10px;" if match_ok else "background-color: #cc3333; padding: 10px;")
        if matched_id:
            self.match_label.setText(f"Match: {matched_id}")
            self.match_label.setStyleSheet("background-color: #339933; padding: 10px;")
        else:
            self.match_label.setText("Match: geen")
            self.match_label.setStyleSheet("background-color: #cc3333; padding: 10px;")

def main():
    app = QApplication(sys.argv)
    dashboard = LiveFeedDashboard()
    start_sensor_thread()

    def frame_callback(img):
        if dashboard.running:
            dashboard.update_frame(img)
        return img

    QTimer.singleShot(100, lambda: camera_module.start_stream(callback=frame_callback, is_running=lambda: dashboard.running))
    dashboard.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
