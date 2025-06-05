import sys
from PyQt5.QtWidgets import QApplication
from newDashboard import MainDashboard
import threading

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainDashboard()

    from logic import camera_module

    def frame_callback(img):
        window.realtime_tab.update_frame(img)
        return img  # geen bewerking

    def start_camera():
        camera_module.start_stream(callback=frame_callback)

    from PyQt5.QtCore import QTimer
    QTimer.singleShot(100, lambda: threading.Thread(target=start_camera, daemon=True).start())

    window.show()

    sys.exit(app.exec_())