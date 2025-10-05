from GUI.mainwindow import Ui_MainWindow
from GUI.PositioningControl import PositioningController
from GUI.GPIOControl import GPIOController

from GUI.ConfigParser import get_config_parser


class HVControlBhv:
    def __init__(self, ui: Ui_MainWindow, positioning_controller: PositioningController, gpio_controller: GPIOController):
        self.ui = ui
        self.positioning_controller = positioning_controller
        self.gpio_controller = gpio_controller

        self.init()
        self.connections()
    
    def init(self):
        pass

    def connections(self):
        self.ui.positioning_power_checkBox.stateChanged.connect(self.toggle_positioning_power)
        self.ui.positioning_home_pushButton.clicked.connect(self.home)
    
    def toggle_positioning_power(self):
        positioning_power_on = self.ui.positioning_power_checkBox.isChecked()
        self.gpio_controller.enable_positioning_power(positioning_power_on)
        self.ui.positioning_home_pushButton.setEnabled(positioning_power_on)
        if not positioning_power_on:
            self.ui.positioning_homing_done_widget.setEnabled(False)

    def home(self):
        self.positioning_controller.home()
        self.ui.positioning_homing_done_widget.setEnabled(True)
