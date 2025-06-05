import sys
from PyQt5.QtWidgets import QApplication
from sensor.height_sensor import start_sensor_thread
from dashboard import LiveFeedDashboard

def main():
    # Start de sensor (leest COM7 continue in aparte thread)
    start_sensor_thread()

    # Start het PyQt-dashboard
    app = QApplication(sys.argv)
    dashboard = LiveFeedDashboard()

    from logic import camera_module

    def frame_callback(img):
        dashboard.update_frame(img)
        return img  # geen bewerking

    from PyQt5.QtCore import QTimer
    QTimer.singleShot(100, lambda: camera_module.start_stream(callback=frame_callback))

    dashboard.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
