from GUI.mainwindow import Ui_MainWindow
from GUI.PositioningControl import PositioningController
from GUI.GPIOControl import GPIOController

from GUI.ConfigParser import get_config_parser


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
        self.ui.positioning_experiment_start_pushButton.clicked.connect(self.start_experiment)
        self.ui.positioning_experiment_stop_pushButton.clicked.connect(self.stop_experiment)

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

        # Disable hard limits when HV is powered on
        self.ui.HV_power_checkBox.stateChanged.connect(self._hv_power_changed)

    def toggle_positioning_power(self):
        positioning_power_on = self.ui.positioning_power_checkBox.isChecked()
        self.gpio_controller.enable_positioning_power(positioning_power_on)
        self.ui.positioning_home_pushButton.setEnabled(positioning_power_on)
        if not positioning_power_on:
            self.ui.positioning_homing_done_widget.setEnabled(False)

    def home(self):
        self.positioning_controller.home()
        self.ui.positioning_homing_done_widget.setEnabled(True)
    
    def start_experiment(self):
        self.ui.positioning_experiment_running_widget.setEnabled(False)
        self.positioning_controller.start_experiment(pump_1_flowrate=self.ui.positioning_pump_1_flow_doubleSpinBox.value(),
                                                     pump_2_flowrate=self.ui.positioning_pump_2_flow_doubleSpinBox.value(),
                                                     stage_feedrate=self.ui.positioning_stage_speed_spinBox.value(),
                                                     stage_amplitude=self.ui.positioning_stage_amplitude_spinBox.value(),
                                                     duration=self.ui.positioning_experiment_duration_spinBox.value())
    
    def calibrate_center(self):
        self.positioning_controller.calibrate_center()
        self.ui.positioning_stage_amplitude_spinBox.setMaximum(abs(self.positioning_controller.stage_center))
    
    def _init_stage_amplitude(self):
        amplitude_limit = get_config_parser().getfloat("Positioning", "StageCenter")
        self.ui.positioning_stage_amplitude_spinBox.setMaximum(abs(amplitude_limit))
    
    def _hv_power_changed(self):
        hv_power_on = self.ui.HV_power_checkBox.isChecked()
        if self.positioning_controller.grbl_streamer.is_connected():
            self.positioning_controller.set_hard_limits(not hv_power_on)
        