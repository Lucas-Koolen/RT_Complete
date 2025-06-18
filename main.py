import sys
import threading
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

from logic import camera_module

from hikvision_sdk.MvCameraControl_class import *

from dashboard import MainDashboard

from logic.communicator import Communicator


class FrameEmitter(QObject):
    """Forward camera frames safely to the GUI thread"""

    frame_ready = pyqtSignal(object)

if __name__ == "__main__":
    app = QApplication(sys.argv)

    cam = MvCamera()

    communicator = Communicator()

    window = MainDashboard(cam, communicator)

    camera_module.start_stream(cam)

    window.show()

    result = app.exec_()
    # shutdown nicely by stopping the camera stream
    camera_module.stop_stream(cam)
    communicator.moveConveyor(1, "STOP")
    communicator.moveConveyor(2, "STOP")
    communicator.movePusher(1, "REV")
    communicator.movePusher(2, "REV")
    communicator.moveFlipper(1, "CLEAR")
    communicator.moveFlipper(2, "CLEAR")

    sys.exit(result)