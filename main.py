import sys
import threading
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

from newDashboard import MainDashboard


class FrameEmitter(QObject):
    """Forward camera frames safely to the GUI thread"""

    frame_ready = pyqtSignal(object)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainDashboard()

    emitter = FrameEmitter()
    emitter.frame_ready.connect(window.realtime_tab.update_frame)

    from logic import camera_module

    def frame_callback(img):
        emitter.frame_ready.emit(img)
        return img  # geen bewerking

    def start_camera():
        camera_module.start_stream(callback=frame_callback)

    QTimer.singleShot(100, lambda: threading.Thread(target=start_camera, daemon=True).start())

    window.show()

    sys.exit(app.exec_())