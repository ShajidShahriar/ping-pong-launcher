"""
serial_controller.py
====================

Robust wrapper around PySerial so the rest of the launcher stack can
speak to an Arduino *or* run safely in mock mode with **zero** hardware.

Key features
------------
• Drop‑in replacement for the original module – public API unchanged.
• A `_NullSerial` stub means every call to `flush()` / `readline()` works
  even when `--mock` is True, so no `AttributeError` crashes.
• Dynamic `set_mock(True|False)` lets you flip modes at runtime.
• All real‑port errors gracefully fall back to mock mode, so the GUI
  never dies if you forget to plug the USB cable.
"""

from __future__ import annotations

import time
from typing import Optional, Union

try:
    import serial  # type: ignore
except ImportError:  # pragma: no cover – allows unit tests without pySerial
    serial = None  # pySerial missing; we will enforce mock mode


class _NullSerial:
    """Do‑nothing stand‑in that mimics the minimal Serial API."""

    def write(self, *_: str | bytes) -> None:  # noqa: D401,E501 – no‑op write
        pass

    def flush(self) -> None:  # noqa: D401 – no‑op flush
        pass

    def readline(self) -> bytes:  # noqa: D401 – always returns empty
        return b""

    @property
    def is_open(self) -> bool:  # noqa: D401 – always open
        return True

    def close(self) -> None:  # noqa: D401 – no‑op close
        pass


SerialLike = Union[_NullSerial, "serial.Serial"]  # type: ignore[name‑defined]


class SerialController:
    """High‑level helper that hides pySerial quirks and mock logic."""

    def __init__(
        self,
        port: str | None = None,
        baud: int = 9600,
        *,
        mock: bool = False,
        timeout: float = 1.0,
    ) -> None:
        self.port = port or "COM1"  # default keeps tests happy
        self.baud = baud
        self.timeout = timeout
        self._mock = mock or serial is None
        self._ser: SerialLike = _NullSerial()

        if not self._mock:
            self.connect()
        else:
            print("[Serial] MOCK mode active – nothing will be sent.")

    # ------------------------------------------------------------------
    # Public properties / helpers
    # ------------------------------------------------------------------
    @property
    def mock(self) -> bool:
        return self._mock

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------
    def connect(self) -> None:
        """Open the real serial port; fall back to mock if it fails."""
        if self._mock:
            # Already in mock mode – just ensure we have a stub object
            self._ser = _NullSerial()
            return

        if serial is None:
            raise RuntimeError("pyserial is not installed; cannot open real port")

        try:
            self._ser = serial.Serial(self.port, self.baud, timeout=self.timeout)
            time.sleep(2)  # allow the Arduino's auto‑reset to finish
            print(f"[Serial] Connected to {self.port} @ {self.baud} baud.")
        except Exception as exc:
            print(f"[Serial] ERROR opening {self.port}: {exc}\n"
                  "           Falling back to MOCK mode.")
            self._ser = _NullSerial()
            self._mock = True

    def close(self) -> None:
        if hasattr(self._ser, "close"):
            self._ser.close()
            print("[Serial] Port closed.")

    def set_mock(self, mock: bool) -> None:
        """Enable / disable mock mode after construction."""
        if self._mock == mock:
            return  # no change
        self.close()
        self._mock = mock
        if not mock:
            self.connect()
        else:
            self._ser = _NullSerial()
            print("[Serial] MOCK mode active – nothing will be sent.")

    # ------------------------------------------------------------------
    # Internal (private) helpers
    # ------------------------------------------------------------------
    def _tx(self, text: str) -> None:
        """Low‑level transmitter – handles mock and real ports."""
        if self._mock:
            print(f"[Serial] MOCK -> {text.strip()}")
        else:
            self._ser.write(text.encode())

    def _rx(self) -> str:
        """Low‑level receiver – returns '' in mock mode."""
        if self._mock:
            return ""
        self._ser.flush()
        return self._ser.readline().decode(errors="ignore").strip()

    # ------------------------------------------------------------------
    # High‑level commands used by the rest of the project
    # ------------------------------------------------------------------
    def write_angle(self, angle: int) -> None:  # noqa: D401 – public API
        """Send a vertical‑servo angle (degrees)."""
        self._tx(f"A,{angle}\n")
        ack = self._rx()
        if ack:
            print("Arduino:", ack)

    def write_wheels(self, upper_pwm: int, lower_pwm: int) -> None:  # noqa: D401
        """Set dual‑wheel speeds (0–255) in one shot."""
        self._tx(f"W,{upper_pwm},{lower_pwm}\n")
        ack = self._rx()
        if ack:
            print("Arduino:", ack)

    def write_gate(self, open_flag: bool) -> None:  # noqa: D401 – toggle gate
        """Open (`True`) or close (`False`) the gate."""
        self._tx(f"G,{1 if open_flag else 0}\n")
        ack = self._rx()
        if ack:
            print("Arduino:", ack)

    # Backwards‑compat alias – some modules call write_raw directly
    def write_raw(self, msg: str) -> None:  # noqa: D401 – wrapper
        self._tx(msg)