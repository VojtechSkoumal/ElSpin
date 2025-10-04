import os
import sys
import traceback

import logging
logger = logging.getLogger(__name__)

from PySide6 import QtGui
from PySide6 import QtWidgets

from GUI.ConfigParser import get_config_parser

from GUI.mainwindow import Ui_MainWindow
from GUI.GPIOControl import GPIOController
from GUI.HVControl import HVController
from GUI.PositioningControl import PositioningController

from GUI.LEDControlBhv import LEDControlBhv
from GUI.HVControlBhv import HVControlBhv


class ElSpinApplication:
    def __init__(self):
        self.app = QtWidgets.QApplication(sys.argv)
        self.app.setStyle("Fusion")

        self.MainWindow = QtWidgets.QMainWindow()
        self.ui: Ui_MainWindow = Ui_MainWindow()
        self.ui.setupUi(self.MainWindow)
        self.MainWindow.setWindowTitle("ElSpin Control")
        self.set_icons()

        self.gpio_controller: GPIOController = None
        self.hv_controller: HVController = None
        self.positioning_controller: PositioningController = None

        self.led_control_bhv: LEDControlBhv = None
        self.hv_control_bhv: HVControlBhv = None

        self.init()
        self.connections()

        self.retval = None

    def set_icons(self):
        icon_folder = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "GUI", "Icons"
        )
        self.MainWindow.setWindowIcon(
            QtGui.QIcon(os.path.join(icon_folder, "spider-web.png")))

    def init(self):
        self.gpio_controller = GPIOController()
        self.hv_controller = HVController(port=get_config_parser().get("HVControl", "COMPort"))
        # self.positioning_controller = PositioningController(self.ui)

        self.led_control_bhv = LEDControlBhv(self.ui, self.gpio_controller)
        self.hv_control_bhv = HVControlBhv(self.ui, self.hv_controller, self.gpio_controller)

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

def except_hook(exc_type, exc_value, exc_tb):
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print("error catched!:")
    print(f"error message:\n{tb}")

    logger.error(f'{exc_value}')


if __name__ == "__main__":
    sys.excepthook = except_hook

    elspin_ui = ElSpinApplication()

    try:
        elspin_ui.show()
    except Exception as ex:
        logger.error(ex)
    finally:
        elspin_ui.gpio_controller.finalize()

    elspin_ui.close()
