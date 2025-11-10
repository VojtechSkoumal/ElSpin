from GUI.mainwindow import Ui_MainWindow
from GUI.HVControl import HVController
from GUI.GPIOControl import GPIOController

from GUI.ConfigParser import get_config_parser


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
        self.ui.HV_power_checkBox.stateChanged.connect(self.toggle_HV_power)
        self.ui.HV_connect_pushButton.clicked.connect(self.connect)

        self.ui.HV_set_target_voltage_pushButton.clicked.connect(
            lambda: self.hv_controller.set_voltage(self.ui.HV_target_voltage_spinBox.value())
        )
        self.ui.HV_enable_pushButton.clicked.connect(self.toggle_HV_enable)
    
    def toggle_HV_power(self):
        hv_power_on = self.ui.HV_power_checkBox.isChecked()
        self.gpio_controller.enable_HV_power(hv_power_on)
        self.update_connect_button()
    
    def update_connect_button(self):
        hv_power_on = self.ui.HV_power_checkBox.isChecked()
        self.ui.HV_connect_pushButton.setEnabled(hv_power_on)
    
    def connect(self):
        try:
            self.hv_controller.connect()
            self.hv_controller.close()  # Close immediately to reset any previous state
            self.hv_controller.connect()
            self.ui.HV_connect_pushButton.setText("Disconnect")
            self.ui.HV_connect_pushButton.clicked.disconnect()
            self.ui.HV_connect_pushButton.clicked.connect(self.disconnect)
            self.ui.HV_connected_groupBox.setEnabled(True)
            self.hv_controller.set_enable_state(False)
            self.hv_controller.set_voltage(0.0)
            
            # Start monitoring with callback
            self.hv_controller.start_voltage_monitor(callback=self.on_voltage_update)
            self.hv_controller.start_current_monitor(callback=self.on_current_update)
        except Exception as e:
            print(f"Failed to connect to HV power supply: {e}")
        
    def disconnect(self):
        self.hv_controller.set_voltage(0.0)
        self.hv_controller.set_enable_state(False)
        self.hv_controller.close()
        self.ui.HV_connect_pushButton.setText("Connect")
        self.ui.HV_connect_pushButton.clicked.disconnect()
        self.ui.HV_connect_pushButton.clicked.connect(self.connect)
        self.ui.HV_connected_groupBox.setEnabled(False)
        self.ui.HV_live_voltage_label.setText("Voltage: NaN V")
        self.ui.HV_live_current_label.setText("Current: NaN μA")

    def toggle_HV_enable(self):
        hv_enable_on = self.ui.HV_enable_pushButton.isChecked()
        self.gpio_controller.enable_HV(hv_enable_on)
        self.ui.HV_enable_pushButton.setText(f'{"Disable" if hv_enable_on else "Enable"}')
        self.ui.HV_state_label.setText(f'{"ON" if hv_enable_on else "OFF"}')
    
    def on_voltage_update(self, voltage):
        """Callback for voltage monitor updates."""
        if voltage is not None:
            self.ui.HV_live_voltage_label.setText(f"Voltage: {int(voltage):,} V")
        else:
            self.ui.HV_live_voltage_label.setText("Voltage: NaN V")
    
    def on_current_update(self, current):
        """Callback for current monitor updates (optional, for future use)."""
        if current is not None:
            self.ui.HV_live_current_label.setText(f"Current: {current:.2f} μA")
        else:
            self.ui.HV_live_current_label.setText("Current: NaN μA")
            pass