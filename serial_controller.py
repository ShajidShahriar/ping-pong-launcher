"""
serial_controller.py
====================

Tiny wrapper around pySerial that lets the rest of the code talk to an
Arduino (or just print to stdout when mock=True).
"""

from __future__ import annotations
import serial
import time


class SerialController:
    def __init__(self, port: str, baud: int = 9600, *, mock: bool = False) -> None:
        self.port  = port
        self.baud  = baud
        self.mock  = mock
        self._ser  = None

    # ------------------------------------------------------------------
    # Basic life-cycle helpers
    # ------------------------------------------------------------------
    def connect(self) -> None:
        if self.mock:
            print("[Serial] Running in MOCK mode -> nothing will be sent.")
            return
        try:
            self._ser = serial.Serial(self.port, self.baud, timeout=1)
            time.sleep(2)  # let the Arduino reset
            print(f"[Serial] Connected to {self.port} @ {self.baud} baud.")
        except Exception as exc:
            print(f"[Serial] ERROR: {exc}")

    def close(self) -> None:
        if self._ser and self._ser.is_open:
            self._ser.close()
            print("[Serial] Port closed.")

    def set_mock(self, mock: bool) -> None:
        """Switch between mock mode and real serial connection."""
        if self.mock == mock:
            return
        # always close any existing connection before switching
        self.close()
        self.mock = mock
        if not mock:
            self.connect()
        else:
            print("[Serial] Running in MOCK mode -> nothing will be sent.")

    # ------------------------------------------------------------------
    # Convenience writers
    # ------------------------------------------------------------------
    def write_angle(self, angle: int) -> None:
        """Send a vertical-servo angle as 'A,<angle>\\n'."""
        self.write_raw(f"A,{angle}\n")

    def write_raw(self, msg: str) -> None:
        """Send any pre-formatted string down the wire."""
        if self.mock:
            print(f"[Serial] MOCK -> {msg.strip()}")
            return
        if self._ser and self._ser.is_open:
            self._ser.write(msg.encode())
