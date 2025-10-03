from GUI.mainwindow import Ui_MainWindow
from GUI.HVControl import HVController
from GUI.GPIOControl import GPIOController


class HVControlBhv:
    def __init__(self, ui: Ui_MainWindow, hv_controller: HVController, gpio_controller: GPIOController):
        self.ui = ui
        self.hv_controller = hv_controller
        self.gpio_controller = gpio_controller


        self.init()
        self.connections()
    
    def init(self):
        pass

    def connections(self):
        pass