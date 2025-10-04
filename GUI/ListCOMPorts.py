import serial.tools.list_ports

def list_com_ports():
    """List available COM ports on the system."""
    return serial.tools.list_ports.comports()


if __name__ == "__main__":
    for port in list_com_ports():
        print(port.device, ":", port.description)