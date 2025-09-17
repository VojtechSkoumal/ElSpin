import serial
import serial.tools.list_ports
import time

HOMING_SETTINGS = {
    '0':10,  # (step pulse, usec)
    '1':25,  # (step idle delay, msec)
    '2':0,  # (step port invert mask:00000000)
    '3':7,  # dir port invert mask (7 = 0b111, all inverted)
    '4':0,  # (step enable invert, bool)
    '5':0,  # (limit pins invert, bool)
    '6':0,  # (probe pin invert, bool)
    
    '10':19,  # status report mask (status, position, hard limits)
    '11':0.010,  # (junction deviation, mm)
    '12':0.002,  # (arc tolerance, mm)
    '13':0,  # (report inches, bool)

    '20':0,  # Soft limits enabled
    '21':1,  # Hard limits enabled
    '22':1,  # Homing cycle enabled
    '23':7,  # Homing dir invert mask (7 = 0b111, all inverted)
    '24':50,  # Homing feed rate
    '25':200,  # Homing seek rate
    '26':250,  # (homing debounce, msec)
    '27':5,  # Homing pull-off (in mm)

    '100':3200,  # X axis steps/mm; (200×32)/2 = 3200; (N*microsteps)/pitch
    '101':3200,  # Y axis steps/mm; (200×32)/2 = 3200; (N*microsteps)/pitch
    '102':200,  # Z axis steps/mm; (200×8)/8 = 200; (N*microsteps)/pitch

    '110':200,  # (x max rate, mm/min)
    '111':200,  # (y max rate, mm/min)
    '112':2000,  # (z max rate, mm/min)
    
    '120':10,  # (x accel, mm/sec^2)
    '121':10,  # (y accel, mm/sec^2)
    '122':100,  # (z accel, mm/sec^2)

    '130':200,  # (x max travel, mm)
    '131':200,  # (y max travel, mm)
    '132':200,  # (z max travel, mm)
}

OPERATING_SETTINGS = {
    '0':10,  # (step pulse, usec)
    '1':25,  # (step idle delay, msec)
    '2':0,  # (step port invert mask:00000000)
    '3':7,  # dir port invert mask (7 = 0b111, all inverted)
    '4':0,  # (step enable invert, bool)
    '5':0,  # (limit pins invert, bool)
    '6':0,  # (probe pin invert, bool)
    
    '10':19,  # status report mask (status, position, hard limits)
    '11':0.010,  # (junction deviation, mm)
    '12':0.002,  # (arc tolerance, mm)
    '13':0,  # (report inches, bool)

    '20':1,  # Soft limits enabled
    '21':1,  # Hard limits enabled
    '22':0,  # Homing cycle disabled
    '23':7,  # Homing dir invert mask (7 = 0b111, all inverted)
    '24':50,  # Homing feed rate
    '25':200,  # Homing seek rate
    '26':250,  # (homing debounce, msec)
    '27':5,  # Homing pull-off (in mm)

    # For pumps (X and Y axes), we set steps per mm such that 1 mm/min = 1 ml/h
    # The actual volume pumped is then V = Distance / 60 
    # syringe_conts = 8 mm/ml
    # ((N*microsteps)/pitch)*syringe_const/mins_in_h
    '100':427,  # X axis (pump 1) - ((200×32)/2)*8/60 = 426.6667
    '101':427,  # Y axis (pump 2) - ((200×32)/2)*8/60 = 426.6667
    # Z axis is not used for pumps, so we set it to a standard value
    '102':200,  # Z axis steps/mm; (200×8)/8 = 200; (N*microsteps)/pitch

    '110':2000,  # (x max rate, mm/min)
    '111':2000,  # (y max rate, mm/min)
    '112':2000,  # (z max rate, mm/min)
    
    '120':10,  # (x accel, mm/sec^2)
    '121':10,  # (y accel, mm/sec^2)
    '122':100,  # (z accel, mm/sec^2)

    '130':135,  # (x max travel, mm)
    '131':135,  # (y max travel, mm)
    '132':200,  # (z max travel, mm)
}

def find_arduino_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "Arduino" in port.description or "CH340" in port.description or "USB Serial" in port.description:
            print(f"Arduino found on port: {port.device}")
            return port.device
    print("Arduino not found")
    return None

SERIAL_PORT = find_arduino_port()
BAUD_RATE = 115200

# Connect to Arduino
arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
time.sleep(2)  # Give Arduino time to reset

print(arduino.read_all().decode().strip())  # Clear any initial data

def send_command(cmd):
    arduino.write(f"{cmd}\n".encode())  # Send command with newline
    time.sleep(0.1)  # Wait for response
    response = arduino.read_all().decode().strip()  # Read response
    return response

def set(address: str, value: float):
    cmd = f"${address}={value}"
    response = send_command(cmd)
    return response

def set_settings(settings: dict):
    for address, value in settings.items():
        response = set(address, value)
        if "ok" not in response.lower():
            print(f"Error setting {address} to {value}: {response}")
        else:
            print(f"Set {address} to {value}: {response}")

def home():
    print("Starting homing cycle...")
    response = send_command('$H')
    while "ok" not in response.lower():
        time.sleep(0.1)
        response = arduino.read_all().decode().strip()
    print("Homing cycle completed.")
    return response


print(send_command('$$'))
print("Setting homing settings...")
set_settings(HOMING_SETTINGS)
print("Homing settings applied successfully.")

print(send_command('$$'))

home()
# print(send_command('$X')) # Unlock the machine

# set_settings(OPERATING_SETTINGS)
# send_command('G91')
# send_command('G1 X60 F2000') # Move pump 1 1ml fast
# send_command('G1 X1 F1') # Move pump 1 1minute at speed 1 ml/hod

