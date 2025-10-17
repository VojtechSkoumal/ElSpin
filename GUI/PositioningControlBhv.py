from GUI.mainwindow import Ui_MainWindow
from GUI.PositioningControl import PositioningController
from GUI.GPIOControl import GPIOController

from GUI.ConfigParser import get_config_parser, edit_config_file


class PositioningControlBhv:
    def __init__(self, ui: Ui_MainWindow, positioning_controller: PositioningController, gpio_controller: GPIOController):
        self.ui = ui
        self.positioning_controller = positioning_controller
        self.gpio_controller = gpio_controller

        self.init()
        self.connections()
    
    def init(self):
        self._init_stage_amplitude()

    def connections(self):
        self.ui.positioning_power_checkBox.stateChanged.connect(self.toggle_positioning_power)
        self.ui.positioning_home_pushButton.clicked.connect(self.home)

        # Pump 1 controls
        self.ui.positioning_pump_1_move_back_10_pushButton.clicked.connect(lambda: self.positioning_controller.simple_move("X", -10))
        self.ui.positioning_pump_1_move_back_1_pushButton.clicked.connect(lambda: self.positioning_controller.simple_move("X", -1))
        self.ui.positioning_pump_1_move_forward_1_pushButton.clicked.connect(lambda: self.positioning_controller.simple_move("X", 1))
        self.ui.positioning_pump_1_move_forward_10_pushButton.clicked.connect(lambda: self.positioning_controller.simple_move("X", 10))

        # Pump 2 controls
        self.ui.positioning_pump_2_move_back_10_pushButton.clicked.connect(lambda: self.positioning_controller.simple_move("Y", -10))
        self.ui.positioning_pump_2_move_back_1_pushButton.clicked.connect(lambda: self.positioning_controller.simple_move("Y", -1))
        self.ui.positioning_pump_2_move_forward_1_pushButton.clicked.connect(lambda: self.positioning_controller.simple_move("Y", 1))
        self.ui.positioning_pump_2_move_forward_10_pushButton.clicked.connect(lambda: self.positioning_controller.simple_move("Y", 10))

        # Stage controls
        self.ui.positioning_stage_move_back_10_pushButton.clicked.connect(lambda: self.positioning_controller.simple_move("Z", -10))
        self.ui.positioning_stage_move_back_1_pushButton.clicked.connect(lambda: self.positioning_controller.simple_move("Z", -1))
        self.ui.positioning_stage_move_forward_1_pushButton.clicked.connect(lambda: self.positioning_controller.simple_move("Z", 1))
        self.ui.positioning_stage_move_forward_10_pushButton.clicked.connect(lambda: self.positioning_controller.simple_move("Z", 10))
        self.ui.positioning_stage_move_to_center_pushButton.clicked.connect(self.positioning_controller.center_stage)
        self.ui.positioning_stage_calibrate_center_pushButton.clicked.connect(self.calibrate_center)

    def toggle_positioning_power(self):
        positioning_power_on = self.ui.positioning_power_checkBox.isChecked()
        self.gpio_controller.enable_positioning_power(positioning_power_on)
        self.ui.positioning_home_pushButton.setEnabled(positioning_power_on)
        if not positioning_power_on:
            self.ui.positioning_homing_done_widget.setEnabled(False)

    def home(self):
        self.positioning_controller.home()
        self.ui.positioning_homing_done_widget.setEnabled(True)
    
    def calibrate_center(self):
        self.positioning_controller.calibrate_center()
        self.ui.positioning_stage_amplitude_spinBox.setMaximum(abs(self.positioning_controller.stage_center))
        try:
            edit_config_file("Positioning", "StageCenter", str(self.positioning_controller.stage_center))
        except FileNotFoundError:
            print(f'Could not save StageCenter to config file. Local config file does not exist.')
    
    def _init_stage_amplitude(self):
        amplitude_limit = get_config_parser().getfloat("Positioning", "StageCenter")
        self.ui.positioning_stage_amplitude_spinBox.setMaximum(abs(amplitude_limit))
