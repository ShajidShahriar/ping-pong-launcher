"""
wheel_controller.py
===================

Handle the two shooter wheels.  Call set_spin('topspin'|'backspin'|'flat')
then fire() to push a PWM pair to the Arduino.

Protocol:  "W,<upper_pwm>,<lower_pwm>\\n"
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple

from serial_controller import SerialController


@dataclass
class SpinPreset:
    name: str
    ratio: Tuple[float, float]  # (upper, lower) multipliers


# three ready-made modes
FLAT      = SpinPreset("flat",     (1.0, 1.0))
TOPSPIN   = SpinPreset("topspin",  (1.3, 1.0))
BACKSPIN  = SpinPreset("backspin", (1.0, 1.3))
_PRESETS  = {p.name: p for p in (FLAT, TOPSPIN, BACKSPIN)}


class WheelController:
    def __init__(
        self,
        serial: SerialController,
        *,
        base_pwm: int = 140,
        upper_pwm: int | None = None,
        lower_pwm: int | None = None,
        max_pwm: int = 255,
        preset: str = "flat",
    ) -> None:
        self.serial = serial
        self.upper_base_pwm = upper_pwm if upper_pwm is not None else base_pwm
        self.lower_base_pwm = lower_pwm if lower_pwm is not None else base_pwm
        self.max_pwm = max_pwm
        self.set_spin(preset)

    # ------------------------------------------------------------------
    # Public controls
    # ------------------------------------------------------------------
    def set_spin(self, preset: str) -> None:
        if preset not in _PRESETS:
            raise ValueError(f"Unknown spin preset: {preset}")
        self._preset = _PRESETS[preset]

    def set_base_pwms(self, upper_pwm: int, lower_pwm: int) -> None:
        """Set the base PWM values for the upper and lower wheels."""
        self.upper_base_pwm = upper_pwm
        self.lower_base_pwm = lower_pwm

    def fire(self) -> None:
        up_mult, low_mult = self._preset.ratio
        up_pwm  = min(int(self.upper_base_pwm * up_mult),  self.max_pwm)
        low_pwm = min(int(self.lower_base_pwm * low_mult), self.max_pwm)
        self.serial.write_raw(f"W,{up_pwm},{low_pwm}\n")

    def current_pwms(self) -> Tuple[int, int]:
        up_mult, low_mult = self._preset.ratio
        return (
            min(int(self.upper_base_pwm * up_mult),  self.max_pwm),
            min(int(self.lower_base_pwm * low_mult), self.max_pwm),
        )
