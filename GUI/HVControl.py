import serial
import time


class HVControllerError(Exception):
    pass

class HVController:
    def __init__(self, port: str = None, baudrate: int = 9600, addr: str = "01", devtype: str = "09", timeout: float = 1.0):
        """
        Initialize the controller.

        :param port: Serial port e.g. "/dev/ttyUSB0" or "COM3", if None, will try to auto-detect
        :param baudrate: Baud rate, default 9600
        :param addr: Address of the unit, two ASCII characters from "00" to "99" ("00" is a broadcast address — all devices on the bus will listen, but they won’t reply)
        :param devtype: Device type code, two ASCII chars, e.g. "09" for MPD30 etc.
        :param timeout: Read timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.addr = addr
        self.devtype = devtype
        self.timeout = timeout

        self.ser = None

        if self.port is None:
            self.port = self._detect_port()
            print(f"Auto-detected port: {self.port}")

    def connect(self):
        try: 
            self.ser = serial.Serial(port=self.port, baudrate=self.baudrate, bytesize=serial.EIGHTBITS,
                                 parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                                 timeout=self.timeout)
            # Allow some settling time
            time.sleep(0.1)
        except serial.SerialException as e:
            raise HVControllerError(f"Failed to open serial port {self.port}: {e}")

    def close(self):
        if self.ser.is_open:
            self.ser.close()
            time.sleep(0.1)
        if self.ser.is_open:
            raise HVControllerError("Failed to close serial port")

    def _detect_port(self):
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if "USB2.0-Ser!" in port.description:
                return port.device
        raise HVControllerError("Could not auto-detect serial port")

    def _checksum(self, addr: str, devtype: str, cmd: str, operator: str, data: str = "") -> str:
        """
        Compute checksum as specified: sum ASCII values of ADDR, DEVTYPE, CMD, OPERATOR, DATA,
        subtract from 0x200, take lower 8 bits, mask bit7 off, set bit6 on. Return two‐char uppercase hex.
        """
        msg = addr + devtype + cmd + operator + data
        total = sum(ord(c) for c in msg)
        checksum = 0x200 - total
        checksum &= 0xFF  # take lower 8 bits
        # clear most significant bit (bit 7)
        checksum &= 0x7F
        # set bit 6
        checksum |= 0x40
        # convert to two‐char uppercase hex, pad with zero if needed
        return f"{checksum:02X}"

    def _build_command(self, cmd: str, operator: str, data: str = "") -> bytes:
        """
        Build the raw bytes to send: <STX><ADDR><DEVTYPE><CMD><OPERATOR><DATA><CSUM><LF>
        """
        STX = chr(0x02)
        LF = chr(0x0A)
        csum = self._checksum(self.addr, self.devtype, cmd, operator, data)
        s = STX + self.addr + self.devtype + cmd + operator + data + csum + LF
        return s.encode('ascii')

    def _send_command(self, cmd: str, operator: str, data: str = "", expect_response: bool = True) -> str:
        """
        Send command, read response. Returns the ASCII response (without STX and LF).
        Raises error on timeout or invalid response/CSUM.
        """
        raw = self._build_command(cmd, operator, data)
        # clear input buffer before sending
        self.ser.reset_input_buffer()
        # send
        self.ser.write(raw)
        # Depending on the command, device responds. For broadcast (ADDR="00") usually no reply except ID?
        if not expect_response:
            return ""
        # read until LF
        resp = self.ser.read_until(b'\n')
        if not resp:
            raise HVControllerError("No response from device")
        # resp is bytes, decode
        try:
            resp_ascii = resp.decode('ascii')
        except UnicodeDecodeError:
            raise HVControllerError(f"Non‐ASCII response: {resp!r}")

        # Response should begin with STX
        if not resp_ascii.startswith(chr(0x02)):
            raise HVControllerError(f"Invalid start of response: {resp_ascii!r}")

        # Strip STX and LF
        body = resp_ascii[1:].rstrip('\n').rstrip('\r')
        # Now you have something like ADDR DEVTYPE CMD = DATA CSUM etc.
        # Optionally verify checksum of response
        # We can parse out the pieces
        # Format: <ADDR><DEVTYPE><CMD><OPERATOR><DATA><CSUM>
        # We'll extract ADDR, DEVTYPE, CMD (2 chars each), operator (1 char), then data (variable), then csum (last 2 chars)
        if len(body) < (2 + 2 + 2 + 1 + 2):  # minimal length
            raise HVControllerError(f"Response too short: {body!r}")

        addr_r = body[0:2]
        devtype_r = body[2:4]
        cmd_r = body[4:6]
        operator_r = body[6:7]
        # everything up to last two chars minus data
        # data is from position 7 up to len(body)-2
        data_r = body[7:-2]
        csum_r = body[-2:]

        # Optionally verify addr/devtype match
        if addr_r != self.addr or devtype_r != self.devtype or cmd_r != cmd:
            # maybe the device is different? We can warn or error
            raise HVControllerError(f"Unexpected response header: addr/devtype/cmd mismatch: got {addr_r},{devtype_r},{cmd_r}")

        # Compute expected checksum for the response
        expected = self._checksum(addr_r, devtype_r, cmd_r, operator_r, data_r)
        if expected.upper() != csum_r.upper():
            raise HVControllerError(f"Checksum mismatch: expected {expected}, got {csum_r}")

        # Data operator is '=' for responses with data, '*' for invalid command, etc.
        return operator_r + data_r  # e.g. "=02500.0"

    #
    # Public commands
    #

    def get_voltage(self) -> float:
        """
        Read present value of output voltage (V1?)
        Returns voltage in volts (float)
        """
        resp = self._send_command(cmd="V1", operator="?", data="")
        # resp should start with '=', then data
        if not resp.startswith('='):
            raise HVControllerError(f"Unexpected response {resp}")
        val_str = resp[1:]
        try:
            return float(val_str)
        except ValueError:
            raise HVControllerError(f"Cannot parse voltage value: {val_str}")

    def set_voltage(self, volts: float) -> None:
        """
        Set desired HV output voltage demand (V1=)
        :param volts: in volts
        """
        # According to examples, format is zero padded to appropriate width. The example: "02500.0" for 2.5kV
        # They use xxxxx.x so one decimal place, total width seems to be 7 chars including decimal point
        # Let’s format: total width 7, with one decimal, pad with leading zeros
        data = f"{volts:07.1f}"
        # e.g. volts=2500.0 -> "02500.0"
        resp = self._send_command(cmd="V1", operator="=", data=data)
        # Optionally check that the echo or response matches
        # The protocol says the unit should respond with same command to confirm
        if not resp.startswith('='):
            raise HVControllerError(f"Unexpected response to set_voltage: {resp}")
        # we could return the set value
        # Optionally parse the returned value if needed

    def get_current_limit(self) -> float:
        """
        Read present value of current limit (I1?)
        Returns current in microamps or amps depending on device spec. The protocol shows I1=xxxxx.x
        """
        resp = self._send_command(cmd="I1", operator="?", data="")
        if not resp.startswith('='):
            raise HVControllerError(f"Unexpected response {resp}")
        val_str = resp[1:]
        try:
            return float(val_str)
        except ValueError:
            raise HVControllerError(f"Cannot parse current limit: {val_str}")

    def set_current_limit(self, current: float) -> None:
        """
        Set current limit (I1=)
        """
        data = f"{current:07.1f}"  # example formatting
        resp = self._send_command(cmd="I1", operator="=", data=data)
        if not resp.startswith('='):
            raise HVControllerError(f"Unexpected response to set_current_limit: {resp}")

    def read_enable_state(self) -> bool:
        """
        Read enable state: EN?
        Returns True if enabled (EN=1), False if disabled (EN=0)
        """
        resp = self._send_command(cmd="EN", operator="?", data="")
        if not resp.startswith('='):
            raise HVControllerError(f"Unexpected response {resp}")
        val = resp[1:]
        if val == '1':
            return True
        elif val == '0':
            return False
        else:
            raise HVControllerError(f"Unexpected EN value: {val}")

    def set_enable_state(self, enable: bool) -> None:
        """
        Enable or disable the output
        """
        val = '1' if enable else '0'
        resp = self._send_command(cmd="EN", operator="=", data=val)
        if not resp.startswith('='):
            raise HVControllerError(f"Unexpected response to set_enable_state: {resp}")

    def get_status(self) -> int:
        """
        Read status register (SR?)
        Returns as integer (hex interpreted)
        """
        resp = self._send_command(cmd="SR", operator="?", data="")
        if not resp.startswith('='):
            raise HVControllerError(f"Unexpected response {resp}")
        # data part is after '='
        val_str = resp[1:]
        try:
            status_vals = bin(int(val_str, 16))[2:].zfill(8)
            status = {
                "Enabled": status_vals[7],
                "Fault": status_vals[6],
                "Over Voltage": status_vals[5],
                "Over Current": status_vals[4],
                "Over Temperature": status_vals[3],
                "Supply Rail": status_vals[2],
                "Hardware Enable": status_vals[1],
                "Software Enable": status_vals[0],
            }
            return status
        except ValueError:
            raise HVControllerError(f"Cannot parse status register: {val_str}")

    def get_voltage_monitor(self) -> float:
        resp = self._send_command(cmd="M0", operator="?", data="")
        if not resp.startswith('='):
            raise HVControllerError(f"Unexpected response {resp}")
        return float(resp[1:])

    def get_current_monitor(self) -> float:
        resp = self._send_command(cmd="M1", operator="?", data="")
        if not resp.startswith('='):
            raise HVControllerError(f"Unexpected response {resp}")
        return float(resp[1:])


if __name__ == "__main__":
    # Example usage
    mpd = HVController()
    try:
        print("Status:", mpd.get_status())
    finally:
        mpd.close()
