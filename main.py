import sys
import threading
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

from logic import camera_module

from hikvision_sdk.MvCameraControl_class import *

from newDashboard import MainDashboard


class FrameEmitter(QObject):
    """Forward camera frames safely to the GUI thread"""

    frame_ready = pyqtSignal(object)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    cam = MvCamera()

    window = MainDashboard(cam)

    camera_module.start_stream(cam)

    window.show()

    result = app.exec_()
    # shutdown nicely by stopping the camera stream
    camera_module.stop_stream(cam)

    sys.exit(result)