import serial
import serial.tools.list_ports
import threading
import time
import queue
import math
import numpy as np

from GRBLSettings import OPERATING_SETTINGS


class PositioningControl:
    def __init__(self):
        self.operating_settings = OPERATING_SETTINGS

        self.grbl_streamer = GRBLStreamer()
        self.grbl_streamer.connect()
        self.set_settings(self.operating_settings)
    
    def home(self):
        print("Starting homing cycle...")
        self.grbl_streamer.clear_stream()
        response = self.grbl_streamer.send_command('$H')
        while "ok" not in response.lower():
            time.sleep(0.1)
            response = self.grbl_streamer.ser.read_all().decode().strip()
        # Move pumps away from endstops
        self.simple_move('X', 10, 1000)
        self.simple_move('Y', 10, 1000)
        print("Homing cycle completed.")
        return response
    
    def simple_move(self, axis: str, distance: float, feedrate: float):
        if axis not in ['X', 'Y', 'Z']:
            raise ValueError("Axis must be 'X', 'Y', or 'Z'")
        self.set_relative_positioning()
        move_cmd = f"G1 {axis}{distance:.3f} F{feedrate:.3f}"
        print(f"Sending move command: {move_cmd}")
        response = self.grbl_streamer.send_command(move_cmd)
        print("Move command response:", response)
        return response
    
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


class GRBLStreamer:
    def __init__(self, port=None, baudrate=115200, buffer_size=128):
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
        self.lock = threading.Lock()

        self.loop_base_gcode = None

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
        self.ser.write(f"{cmd}\n".encode())
        time.sleep(0.1)  # Wait for response
        response = self.ser.read_all().decode().strip()
        return response

    def _send_loop(self):
        """Send G-code from queue, keeping GRBL buffer full."""
        while not self.stop_flag.is_set():
            try:
                cmd = self.cmd_queue.get(timeout=0.05)
            except queue.Empty:
                continue

            while self.used_buffer + len(cmd) + 1 > self.buffer_size and not self.stop_flag.is_set():
                time.sleep(0.01)

            if self.stop_flag.is_set():
                break

            self.ser.write((cmd + "\n").encode())
            with self.lock:
                self.used_buffer += len(cmd) + 1

        print("[GRBL] Send loop stopped.")

    def _read_loop(self):
        """Read GRBL responses and manage buffer space."""
        while not self.stop_flag.is_set():
            line = self.ser.readline().decode().strip()
            if line:
                print(f"< {line}")
                if line.startswith("ok") or line.startswith("error"):
                    with self.lock:
                        # free space in buffer
                        self.used_buffer = max(0, self.used_buffer - 1)
                if "ALARM" in line:
                    print("[GRBL] Alarm detected!")
                    self.stop_flag.set()
        print("[GRBL] Read loop stopped.")

    def start(self):
        """Start streaming threads."""
        self.stop_flag.clear()
        self.send_thread = threading.Thread(target=self._send_loop, daemon=True)
        self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.send_thread.start()
        self.read_thread.start()

    def send_move_to_queue(self, gcode):
        """Queue a G-code command for sending."""
        self.cmd_queue.put(gcode)

    def stop(self):
        """Stop streaming."""
        print("[GRBL] Stopping...")
        self.stop_flag.set()
        if self.send_thread:
            self.send_thread.join()
        if self.read_thread:
            self.read_thread.join()
        print("[GRBL] All threads stopped.")

    def close(self):
        """Close serial port."""
        if self.ser:
            self.ser.close()
            print("[GRBL] Disconnected.")
    
    def find_arduino_port(self):
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if "Arduino" in port.description or "CH340" in port.description or "USB Serial" in port.description:
                print(f"Arduino found on port: {port.device}")
                return port.device
        print("Arduino not found")
        return None
    
    def clear_stream(self):
        """Clear all messages from GRBL."""
        self.ser.read_all()

if __name__ == "__main__":
    positioning_control = PositioningControl()

    # # Test homing and move
    # positioning_control.home()
    # # positioning_control.grbl_streamer.send_command('$X') # Unlock the machine
    # print(positioning_control.grbl_streamer.send_command('G91'))
    # print(positioning_control.grbl_streamer.send_command('G1 Z10 F1000'))

    # Test multiaxis move
    z_dist = -10  # mm
    z_feedrate = 100  # mm/min
    x_feedrate = 1  # mm/min (ml/h in fact)
    y_feedrate = 1  # mm/min (ml/h in fact)
    x_dist, y_dist, common_feedrate = PositioningControl.match_axes_by_feedrate(z_dist, z_feedrate, x_feedrate, y_feedrate)
    print(f"Calculated distances: X={x_dist:.3f}, Y={y_dist:.3f}, Feedrate={common_feedrate:.3f}")

    # positioning_control.grbl_streamer.send_command('$X') # Unlock the machine
    # positioning_control.grbl_streamer.send_command('G91')
    # positioning_control.grbl_streamer.send_command(f'G1 X{x_dist:.3f} Y{y_dist:.3f} Z{z_dist:.3f} F{common_feedrate:.3f}')

