import time
import RPi.GPIO as GPIO


class GPIOControllerError(Exception):
    pass

class GPIOController:
    def __init__(self):
        self.HV_power_enable_pin = 17
        self.HV_enable_pin = 27
        self.LED_power_enable_pin = 22
        self.positioning_power_enable_pin = 23
        self.rotation_power_enable_pin = 24

        self.initialize()
    
    def initialize(self):
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.HV_power_enable_pin, GPIO.OUT)
            GPIO.setup(self.HV_enable_pin, GPIO.OUT)
            GPIO.setup(self.LED_power_enable_pin, GPIO.OUT)
            GPIO.setup(self.positioning_power_enable_pin, GPIO.OUT)
            GPIO.setup(self.rotation_power_enable_pin, GPIO.OUT)

            GPIO.output(self.HV_power_enable_pin, GPIO.HIGH)
            GPIO.output(self.HV_enable_pin, GPIO.HIGH)
            GPIO.output(self.LED_power_enable_pin, GPIO.HIGH)
            GPIO.output(self.positioning_power_enable_pin, GPIO.HIGH)
            GPIO.output(self.rotation_power_enable_pin, GPIO.HIGH)
        except Exception as e:
            raise GPIOControllerError(f"Failed to initialize GPIO pins: {e}")

    def enable_HV_power(self, enable: bool):
        GPIO.output(self.HV_power_enable_pin, GPIO.LOW if enable else GPIO.HIGH)
    
    def enable_HV(self, enable: bool):
        GPIO.output(self.HV_enable_pin, GPIO.LOW if enable else GPIO.HIGH)
    
    def enable_LED_power(self, enable: bool):
        GPIO.output(self.LED_power_enable_pin, GPIO.LOW if enable else GPIO.HIGH)
    
    def enable_positioning_power(self, enable: bool):
        GPIO.output(self.positioning_power_enable_pin, GPIO.LOW if enable else GPIO.HIGH)
    
    def enable_rotation_power(self, enable: bool):
        GPIO.output(self.rotation_power_enable_pin, GPIO.LOW if enable else GPIO.HIGH)

    def cleanup(self):
        GPIO.cleanup()


if __name__ == "__main__":
    # Example usage
    gpio = GPIOController()
    try:
        gpio.enable_LED_power(True)
        time.sleep(10)
        gpio.enable_LED_power(False)
    finally:
        gpio.cleanup()

