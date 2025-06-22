# serial_controller.py

import serial
import serial.tools.list_ports
import time
import logging


class SerialController:
    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 1.0, mock=False):
        self.mock = mock
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.conn = None
        self.logger = logging.getLogger(self.__class__.__name__)

    def connect(self):
        if self.mock:
            self.logger.info("Mock serial: no hardware connection")
            return True
        try:
            self.conn = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            time.sleep(2)
            self.logger.info(f"Connected to Arduino on {self.port}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to {self.port}: {e}")
            return False

    def write(self, msg: str):
        if self.mock:
            self.logger.debug(f"Mock write: {msg.strip()}")
            return
        if self.conn and self.conn.is_open:
            self.conn.write(msg.encode())
            self.logger.debug(f"Wrote to serial: {msg.strip()}")

    def readline(self) -> str:
        if self.mock:
            return "OK"
        if self.conn:
            resp = self.conn.readline().decode().strip()
            self.logger.debug(f"Read from serial: {resp}")
            return resp
        return ""

    def close(self):
        if self.conn and self.conn.is_open:
            self.conn.close()
            self.logger.info("Serial port closed")

