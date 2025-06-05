import sys
from PyQt5.QtWidgets import QApplication
from dashboard import RotationDashboard

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RotationDashboard()
    window.show()
    sys.exit(app.exec_())
