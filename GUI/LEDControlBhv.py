from GUI.mainwindow import Ui_MainWindow
from GUI.GPIOControl import GPIOController


class LEDControlBhv:
    def __init__(self, ui: Ui_MainWindow, gpio_controller: GPIOController):
        self.ui = ui
        self.gpio_controller = gpio_controller
    
        self.led_on = False

        self.init()
        self.connections()
    
    def init(self):
        self.set_button_text()

    def connections(self):
        self.ui.LED_power_pushButton.clicked.connect(self.toggle_leds)
    
    def toggle_leds(self):
        self.led_on = not self.led_on
        self.gpio_controller.enable_LED_power(self.led_on)
        self.set_button_text()

    def set_button_text(self):
        self.ui.LED_power_pushButton.setText(f'Power LEDs {"OFF" if self.led_on else "ON"}')