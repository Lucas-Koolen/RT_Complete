import sys
from PyQt5.QtWidgets import QApplication
from newDashboard import RotationDashboard

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RotationDashboard()
    sys.exit(app.exec_())


    # Start de sensor (leest COM7 continue in aparte thread)
    start_sensor_thread()

    from logic import camera_module

    def frame_callback(img):
        window.update_frame(img)
        return img  # geen bewerking

    from PyQt5.QtCore import QTimer
    QTimer.singleShot(100, lambda: camera_module.start_stream(callback=frame_callback))

    window.show()

    sys.exit(app.exec_())


#if __name__ == "__main__":
#    app = QApplication(sys.argv)
#    main_win = MainDashboard()
#    main_win.show()
#    sys.exit(app.exec_())