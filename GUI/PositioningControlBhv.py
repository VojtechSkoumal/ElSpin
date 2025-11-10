import time
import threading

from GUI.mainwindow import Ui_MainWindow
from GUI.PositioningControl import PositioningController
from GUI.GPIOControl import GPIOController
from GUI.ConfigParser import get_config_parser


class PositioningControlBhv:
    def __init__(self, ui: Ui_MainWindow, positioning_controller: PositioningController, gpio_controller: GPIOController):
        self.ui = ui
        self.positioning_controller = positioning_controller
        self.gpio_controller = gpio_controller

        self._experiment_timer: threading.Timer | None = None
        self._experiment_start_time: float | None = None
        self._experiment_duration_seconds: float = 0
        self._update_timer: threading.Timer | None = None

        self.init()
        self.connections()
    
    def init(self):
        self._init_stage_amplitude()
        self._init_send_command_widget()

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

        # Disable hard limits and Homing when HV is powered on
        self.ui.HV_power_checkBox.stateChanged.connect(self._hv_power_changed)

        # DEV commands
        self.ui.positioning_send_command_pushButton.clicked.connect(
            lambda: self.positioning_controller.grbl_streamer.send_command(self.ui.positioning_send_command_lineEdit.text())
        )

    def toggle_positioning_power(self, positioning_power_on):
        self.gpio_controller.enable_positioning_power(positioning_power_on)
        self.ui.positioning_home_pushButton.setEnabled(positioning_power_on and not self.ui.HV_power_checkBox.isChecked())
        if not positioning_power_on:
            self.ui.positioning_homing_done_widget.setEnabled(False)

    def home(self):
        self.positioning_controller.home()
        self.ui.positioning_homing_done_widget.setEnabled(True)
    
    def start_experiment(self):
        self.ui.positioning_experiment_running_widget.setEnabled(False)
        self._clean_experiment_timer()
        self.positioning_controller.start_experiment(pump_1_flowrate=self.ui.positioning_pump_1_flow_doubleSpinBox.value(),
                                                     pump_2_flowrate=self.ui.positioning_pump_2_flow_doubleSpinBox.value(),
                                                     stage_feedrate=self.ui.positioning_stage_speed_spinBox.value(),
                                                     stage_amplitude=self.ui.positioning_stage_amplitude_spinBox.value())
        duration = self.ui.positioning_experiment_duration_spinBox.value()
        if duration > 0:
            self._experiment_duration_seconds = duration * 60  # Convert minutes to seconds
            self._experiment_start_time = time.time()
            self._experiment_timer = threading.Timer(self._experiment_duration_seconds, self.stop_experiment)
            self._experiment_timer.daemon = True
            self._experiment_timer.start()
            # Start the update timer to refresh remaining time display
            self._update_remaining_time()
            self._schedule_update_timer()

    def stop_experiment(self):
        print('Stopping experiment...')
        self._clean_experiment_timer()
        self._clean_update_timer()
        self._experiment_start_time = None
        self.positioning_controller.grbl_streamer.stop()
        time.sleep(0.5)  # Give some time to stop
        self.ui.positioning_experiment_running_widget.setEnabled(True)
    
    def _clean_experiment_timer(self):
        """Cancel and clear any existing experiment timer."""
        if self._experiment_timer is not None:
            try:
                self._experiment_timer.cancel()
            except Exception:
                pass
            finally:
                self._experiment_timer = None
    
    def _clean_update_timer(self):
        """Cancel and clear any existing update timer."""
        if self._update_timer is not None:
            try:
                self._update_timer.cancel()
            except Exception:
                pass
            finally:
                self._update_timer = None
    
    def _schedule_update_timer(self):
        """Schedule the next update of the remaining time display."""
        self._clean_update_timer()
        if self._experiment_start_time is not None:
            self._update_timer = threading.Timer(1.0, self._update_and_reschedule)
            self._update_timer.daemon = True
            self._update_timer.start()
    
    def _update_and_reschedule(self):
        """Update the remaining time and schedule the next update."""
        self._update_remaining_time()
        self._schedule_update_timer()
    
    def _update_remaining_time(self):
        """Calculate and display the remaining time."""
        if self._experiment_start_time is None:
            return
        
        elapsed = time.time() - self._experiment_start_time
        remaining = max(0, self._experiment_duration_seconds - elapsed)
        
        # Format remaining time as MM:SS
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        time_str = f"{minutes:01d}:{seconds:02d}"
        
        self.ui.positioning_experiment_remaining_time_value_label.setText(time_str)
        
        # If time is up, ensure we stop
        if remaining <= 0:
            self._clean_update_timer()

    def calibrate_center(self):
        self.positioning_controller.calibrate_center()
        self.ui.positioning_stage_amplitude_spinBox.setMaximum(abs(self.positioning_controller.stage_center))
    
    def _init_stage_amplitude(self):
        amplitude_limit = get_config_parser().getfloat("Positioning", "StageCenter")
        self.ui.positioning_stage_amplitude_spinBox.setMaximum(abs(amplitude_limit))
    
    def _hv_power_changed(self, hv_power_on):
        self.ui.positioning_home_pushButton.setEnabled(not hv_power_on)
        if self.positioning_controller.grbl_streamer.is_connected():
            self.positioning_controller.set_hard_limits(not hv_power_on)
        
    def _init_send_command_widget(self):
        self.ui.positioning_send_command_groupBox.setVisible(get_config_parser().getboolean("DEV", "EnablePositioningCMDs"))
        