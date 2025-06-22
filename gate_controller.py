"""gate_controller.py
====================

Simple wrapper to open/close the ping pong feed gate via SerialController.
Sends "G,1" for open and "G,0" for close.
"""

from __future__ import annotations

from serial_controller import SerialController

class GateController:
    def __init__(self, serial: SerialController) -> None:
        self.serial = serial

    def open(self) -> None:
        """Command the gate to open."""
        self.serial.write_raw("G,1\n")

    def close(self) -> None:
        """Command the gate to close."""
        self.serial.write_raw("G,0\n")
