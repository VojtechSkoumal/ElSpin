import os
import sys
import traceback

import logging
logger = logging.getLogger(__name__)

from PySide6 import QtGui
from PySide6 import QtWidgets

from GUI.ConfigParser import get_config_parser

# import GUI.UiToPyConverter
from GUI.mainwindow import Ui_MainWindow


class ElSpinApplication:
    def __init__(self):
        self.app = QtWidgets.QApplication(sys.argv)
        self.app.setStyle("Fusion")

        self.MainWindow = QtWidgets.QMainWindow()
        self.ui: Ui_MainWindow = Ui_MainWindow()
        self.ui.setupUi(self.MainWindow)
        self.MainWindow.setWindowTitle("ElSpin Control")
        self.set_icons()

        self.detector = None
        self.init()
        self.connections()

        config_parser = get_config_parser()

        self.retval = None

    def set_icons(self):
        icon_folder = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "GUI", "Icons"
        )
        self.MainWindow.setWindowIcon(
            QtGui.QIcon(os.path.join(icon_folder, "spider-web.png")))

    def init(self):
        pass

    def connections(self):
        pass

    def hide_log_window(self, state):
        self.ui.logs_frame.setVisible(state)

    def show(self):
        self.MainWindow.showMaximized()

        self.retval = self.app.exec()
        print(f"Event loop exited. RetVal: {self.retval}")
        sys.exit(self.retval)

    def close(self):
        sys.exit(self.retval)

    def close_devices(self):
        # todo disconnect HV control and positioning
        pass

def except_hook(exc_type, exc_value, exc_tb):
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print("error catched!:")
    print(f"error message:\n{tb}")

    logger.error(f'{exc_value}')


if __name__ == "__main__":
    sys.excepthook = except_hook

    timepix_ui = ElSpinApplication()

    try:
        timepix_ui.show()
    except Exception as ex:
        logger.error(ex)
    finally:
        timepix_ui.close_devices()

    timepix_ui.close()
