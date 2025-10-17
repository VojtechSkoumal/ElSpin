from dataclasses import dataclass
import serial
import serial.tools.list_ports
import threading
import time
import queue
import math
import numpy as np
import re

from GUI.ConfigParser import get_config_parser
from GUI.GRBLSettings import OPERATING_SETTINGS


@dataclass
class Position:
    x: float
    y: float
    z: float

    def __str__(self):
        return f"X: {self.x:.3f}, Y: {self.y:.3f}, Z: {self.z:.3f}"


class PositioningController:
    def __init__(self):
        self.operating_settings = OPERATING_SETTINGS

        self.grbl_streamer = GRBLStreamer(port=get_config_parser().get('Positioning', 'COMPort'))
        self.grbl_streamer.connect()
        self.grbl_streamer.loop_method = self.dummy_loop  # Example loop method
        self.set_settings(self.operating_settings)

        self.default_simple_move_feedrate = get_config_parser().getfloat('Positioning', 'DefaultSimpleMoveFeedrate', fallback=1000.0)
        self.stage_center = get_config_parser().getint('Positioning', 'StageCenter', fallback=250)
    
    def home(self):
        print("Starting homing cycle...")
        self.grbl_streamer.clear_stream()
        response = self.grbl_streamer.send_command('$H')
        while "ok" not in response.lower():
            time.sleep(0.1)
            response = self.grbl_streamer.ser.read_all().decode().strip()
        # Move pumps away from endstops
        self.simple_move('X', 5, 1000)
        self.simple_move('Y', 5, 1000)
        print("Homing cycle completed.")
        return response
    
    def simple_move(self, axis: str, distance: float, feedrate: float = None):
        if axis not in ['X', 'Y', 'Z']:
            raise ValueError("Axis must be 'X', 'Y', or 'Z'")
        if feedrate is None:
            feedrate = self.default_simple_move_feedrate
        print(f'Status before move: {self.grbl_streamer.get_status()}')
        self.set_relative_positioning()
        if axis != 'Z':
            # For pumps (X and Y), steps per mm is set such that 1 mm/h is in fact 1 ml/h
            # For simple move the distance must be multiplied to mach the desired distance in reality
            distance = distance * 3200 / 427  # Using operating settings steps/mm ratio
        move_cmd = f"G1 {axis}{distance:.3f} F{feedrate:.3f}"
        print(f"Sending move command: {move_cmd}")
        response = self.grbl_streamer.send_command(move_cmd)
        print("Move command response:", response)
        return response

    def absolute_move(self, axis: str, position: float, feedrate: float = None):
        if axis not in ['X', 'Y', 'Z']:
            raise ValueError("Axis must be 'X', 'Y', or 'Z'")
        if feedrate is None:
            feedrate = self.default_simple_move_feedrate
        print(f'Status before move: {self.grbl_streamer.get_status()}')
        self.set_absolute_positioning()
        move_cmd = f"G1 {axis}{position:.3f} F{feedrate:.3f}"
        print(f"Sending move command: {move_cmd}")
        response = self.grbl_streamer.send_command(move_cmd)
        print("Move command response:", response)
        return response

    def center_stage(self):
        self.absolute_move('Z', self.stage_center)

    def calibrate_center(self):
        pos = self.get_absolute_positions()
        self.stage_center = pos.z / 2
        config = get_config_parser()
        config.set('Positioning', 'StageCenter', str(self.stage_center))
        with open('config.ini', 'w') as configfile:
            config.write(configfile)
        print(f"Calibrated stage center to: {self.stage_center}")
        self.center_stage()
    
    def get_absolute_positions(self):
        status = self.grbl_streamer.get_status()
        # response pattern: <Idle,MPos:0.000,0.000,0.000,WPos:0.000,0.000,0.000,Lim:000>
        match = re.search(r"MPos:([\d\.\-]+),([\d\.\-]+),([\d\.\-]+)", status)
        if match:
            x_pos, y_pos, z_pos = map(float, match.groups())
            return Position(x_pos, y_pos, z_pos)
        raise ValueError("Could not parse position from GRBL status: " + status)

    def set_relative_positioning(self):
        response = self.grbl_streamer.send_command("G91")  # Relative positioning
        print("Set to relative positioning:", response)
        return response

    def set_absolute_positioning(self):
        response = self.grbl_streamer.send_command("G90")  # Absolute positioning
        print("Set to absolute positioning:", response)
        return response

    def set_settings(self, settings: dict):
        for address, value in settings.items():
            cmd = f"${address}={value}"
            response = self.grbl_streamer.send_command(cmd)
            if "ok" not in response.lower():
                print(f"Error setting {address} to {value}: {response}")
            else:
                print(f"Set {address} to {value}: {response}")
    
    def match_axes_by_feedrate(z_dist, fz, fx, fy):
        """
        Given a Z distance and per-axis feedrates, compute:
        - X distance (always positive - direction invariant)
        - Y distance (always positive - direction invariant)
        - Common GRBL feedrate
        
        Parameters:
        z_dist : float -> Z axis travel distance (mm)
        fz     : float -> Z axis feedrate (mm/min)
        fx     : float -> X axis feedrate (mm/min)
        fy     : float -> Y axis feedrate (mm/min)
        
        Returns:
        (x_dist, y_dist, common_feedrate)
        """
        # Time required for Z move
        time_min = z_dist / fz  # minutes
        
        # Distances for X and Y based on their feedrates and same time
        x_dist = np.abs(fx * time_min)
        y_dist = np.abs(fy * time_min)
        
        # Common feedrate = vector sum of axis velocities
        common_feedrate = math.sqrt(fx**2 + fy**2 + fz**2)
        
        return x_dist, y_dist, common_feedrate
    
    def dummy_loop(self, previous_command: str):
        """Example loop method to be assigned to GRBLStreamer.loop_method"""
        if not previous_command:
            return 'G1 X0 Y0 Z10 F500'  # Initial command
        previous_coords = self.parse_move_command(previous_command)
        return f'G1 X{previous_coords.get("X", 0)} Y{previous_coords.get("Y", 0)} Z{-previous_coords.get("Z", 0)} F{previous_coords.get("F", 0)}'
    
    def parse_move_command(self, command: str):
        """Parse a G-code move command into its components."""
        if not command.startswith('G1'):
            raise ValueError("Only G1 commands are supported.")
        parts = command.split(' ')
        coords = {}
        for part in parts[1:]:
            axis = part[0]
            value = float(part[1:])
            coords[axis] = value
        return coords

class GRBLStreamer:
    def __init__(self, port=None, baudrate=115200, buffer_size=64):
        self.port = port
        if not self.port:
            self.port = self.find_arduino_port()
            if not self.port:
                raise ValueError("No Arduino found. Please specify a valid port.")
        self.baudrate = baudrate
        self.buffer_size = buffer_size
        self.ser = None
        self.send_thread = None
        self.read_thread = None
        self.stop_flag = threading.Event()
        self.cmd_queue = queue.Queue()
        self.used_buffer = 0
        self.buffer_data_lock = threading.Lock()
        self.sent_cmd_lengths = queue.Queue()  # Track lengths of sent commands
        self.loop_method = None
        self.last_command = None
        self.ser_communication_lock = threading.Lock()

    def connect(self):
        self.ser = serial.Serial(self.port, self.baudrate)
        self.on_connection_check()
    
    def on_connection_check(self):
        # Read GRBL startup message and extract version
        timeout = time.time() + 5  # 5 seconds timeout
        while True:
            startup_msg = self.ser.readline().decode().strip()
            if startup_msg:
                self.clear_stream()
                break
            if time.time() > timeout:
                raise TimeoutError("No response from GRBL on connection check.")
        version = None
        if "Grbl" in startup_msg:
            # Example: "Grbl 1.1h ['$' for help]"
            parts = startup_msg.split()
            if len(parts) >= 2 and parts[0] == "Grbl":
                version = parts[1]
                print(f"[GRBL] Connected. Version: {version if version else 'Unknown'}")
        else:
            raise ValueError("Unexpected startup message from GRBL: " + startup_msg)
    
    def send_command(self, cmd):
        if not self.ser:
            raise ConnectionError("Serial port not connected.")
        with self.ser_communication_lock:
            self.ser.write(f"{cmd}\n".encode())
            time.sleep(0.1)  # Wait for response
            response = self.ser.read_all().decode().strip()
        return response

    def _send_loop(self):
        """Send G-code from queue, keeping GRBL buffer full."""
        while not self.stop_flag.is_set():
            with self.buffer_data_lock:
                cmd = self.loop_method(previous_command=self.last_command)
            while self.used_buffer + len(cmd) + 1 > self.buffer_size and not self.stop_flag.is_set():
                time.sleep(0.01)

            if self.stop_flag.is_set():
                break

            with self.ser_communication_lock:
                self.ser.write((cmd + "\n").encode())
            with self.buffer_data_lock:
                cmd_len = len(cmd) + 1
                self.used_buffer += cmd_len
                self.sent_cmd_lengths.put(cmd_len)
                self.last_command = cmd

        print("[GRBL] Send loop stopped.")

    def _read_loop(self):
        """Read GRBL responses and manage buffer space."""
        while not self.stop_flag.is_set():
            with self.ser_communication_lock:
                line = self.ser.readline().decode().strip()
            if line:
                print(f"Reader: {line}")
                if line.startswith("ok") or line.startswith("error"):
                    with self.buffer_data_lock:
                        # free space in buffer
                        if not self.sent_cmd_lengths.empty():
                            cmd_len = self.sent_cmd_lengths.get()
                            self.used_buffer = max(0, self.used_buffer - cmd_len)
                if "ALARM" in line:
                    print("[GRBL] Alarm detected!")
                    self.stop_flag.set()
            time.sleep(0.5)
        print("[GRBL] Read loop stopped.")

    def start(self):
        """Start streaming threads."""
        if not "Idle" in self.get_status():
            raise RuntimeError("GRBL not in Idle state. Cannot start streaming.")
        if self.loop_method is None:
            raise ValueError("No loop method defined for GRBLStreamer.")
        self.stop_flag.clear()
        self.send_command('G91')  # Set to relative positioning before starting
        self.send_thread = threading.Thread(target=self._send_loop, daemon=True)
        self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.send_thread.start()
        self.read_thread.start()

    def send_move_to_queue(self, gcode):
        """Queue a G-code command for sending."""
        self.cmd_queue.put(gcode)

    # def pause(self):
    #     """Pause streaming."""
    #     if not "Run" in self.send_command('?'):
    #         print("[GRBL] Not moving, cannot pause.")
    #         return
    #     print("[GRBL] Pausing...")
    #     self.send_command('!')  # Pause command in GRBL
    
    # def resume(self):
    #     """Resume streaming."""
    #     if not "Hold" in self.send_command('?'):
    #         print("[GRBL] Not paused, cannot resume.")
    #         return
    #     print("[GRBL] Resuming...")
    #     self.send_command('~')  # Resume command in GRBL

    def stop(self):
        """Stop streaming and send soft reset to GRBL."""
        print("[GRBL] Stopping...")
        self.stop_flag.set()
        self.soft_reset()
        # Wait for threads to finish
        if self.send_thread:
            self.send_thread.join()
        if self.read_thread:
            self.read_thread.join()
        # Clear command queue and buffer
        with self.buffer_data_lock:
            while not self.cmd_queue.empty():
                self.cmd_queue.get()
            while not self.sent_cmd_lengths.empty():
                self.sent_cmd_lengths.get()
            self.used_buffer = 0
            self.last_command = None
        self.send_command('$X')  # Unlock the machine
        print("[GRBL] All threads stopped and buffers cleared.")

    def soft_reset(self):
        """Send soft reset to GRBL."""
        print("[GRBL] Sending soft reset...")
        self.send_command('\x18')  # Ctrl+X
        self.send_command('$X')    # Unlock
        
    def close(self):
        """Close serial port."""
        if self.ser:
            self.ser.close()
            print("[GRBL] Disconnected.")
    
    def find_arduino_port(self):
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if "USB Serial" in port.description:
                print(f"Arduino found on port: {port.device}")
                return port.device
        print("Arduino not found")
        return None
    
    def clear_stream(self):
        """Clear all messages from GRBL."""
        self.ser.read_all()
    
    def get_status(self):
        """Get current status from GRBL."""
        return self.send_command('?')


if __name__ == "__main__":
    positioning_control = PositioningController()

    # # Test homing and move
    # positioning_control.home()
    # # positioning_control.grbl_streamer.send_command('$X') # Unlock the machine
    # print(positioning_control.grbl_streamer.send_command('G91'))
    # print(positioning_control.grbl_streamer.send_command('G1 Z10 F1000'))

    # Test Pause and Soft Reset
    # positioning_control.grbl_streamer.send_command('$X') # Unlock the machine
    # print(positioning_control.grbl_streamer.send_command('G91'))
    # print(positioning_control.grbl_streamer.send_command('G1 Z20 F100'))
    # print(positioning_control.grbl_streamer.send_command('?'))
    # time.sleep(1)
    # print(positioning_control.grbl_streamer.send_command('!'))  # Pause
    # print(positioning_control.grbl_streamer.send_command('?'))
    # time.sleep(2)
    # print(positioning_control.grbl_streamer.send_command('~'))  # Resume
    # print(positioning_control.grbl_streamer.send_command('?'))

    # positioning_control.grbl_streamer.send_command('$X') # Unlock the machine
    # print(positioning_control.grbl_streamer.send_command('G1 Z-20 F100'))
    # print(positioning_control.grbl_streamer.send_command('?'))
    # time.sleep(1)
    # print(positioning_control.grbl_streamer.send_command('\x18'))  # Soft Reset
    # print(positioning_control.grbl_streamer.send_command('?'))
    # time.sleep(1)
    # positioning_control.grbl_streamer.send_command('$X') # Unlock the machine
    # print(positioning_control.grbl_streamer.send_command('?'))
    # print(positioning_control.grbl_streamer.send_command('G91'))
    # print(positioning_control.grbl_streamer.send_command('G1 Z10 F100'))
    

    # # Test multiaxis move
    # z_dist = -10  # mm
    # z_feedrate = 100  # mm/min
    # x_feedrate = 1  # mm/min (ml/h in fact)
    # y_feedrate = 1  # mm/min (ml/h in fact)
    # x_dist, y_dist, common_feedrate = PositioningControl.match_axes_by_feedrate(z_dist, z_feedrate, x_feedrate, y_feedrate)
    # print(f"Calculated distances: X={x_dist:.3f}, Y={y_dist:.3f}, Feedrate={common_feedrate:.3f}")

    # positioning_control.grbl_streamer.send_command('$X') # Unlock the machine
    # positioning_control.grbl_streamer.send_command('G91')
    # positioning_control.grbl_streamer.send_command(f'G1 X{x_dist:.3f} Y{y_dist:.3f} Z{z_dist:.3f} F{common_feedrate:.3f}')

    # Test continuous looped movement
    positioning_control.grbl_streamer.send_command('$X') # Unlock the machine
    positioning_control.grbl_streamer.start()
    time.sleep(5)  # Let it run for a while
    positioning_control.grbl_streamer.stop()
    time.sleep(5)  # Let it run for a while
    positioning_control.grbl_streamer.start()
    time.sleep(5)  # Let it run for a while
    positioning_control.grbl_streamer.stop()

