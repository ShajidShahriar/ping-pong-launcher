"""utils.py
Small collection of helper functions that are shared by several modules.
None of this is fancy – the whole point is to avoid copy‑pasting the same
few one‑liners everywhere else.
"""

from __future__ import annotations

import math
from typing import Tuple

import cv2  # OpenCV is already a project dependency

__all__ = [
    "pad_square",
    "clamp",
    "map_value",
    "map_to_servo_angle",
    "calculate_servo_point",
]


# ----------------------------------------------------------------------
# Image helpers
# ----------------------------------------------------------------------

def pad_square(image, colour: Tuple[int, int, int] = (0, 0, 0)):
    """Return *image* padded to a square canvas.

    OpenCV frames are numpy arrays shaped (h, w, 3).  If the width and
    height differ we add borders so that the result is a square, using the
    supplied *colour* (BGR order).  This keeps the subject centred and makes
    later math easier because *width* equals *height*.
    """
    h, w = image.shape[:2]
    if h == w:
        return image

    size = max(h, w)
    top = (size - h) // 2
    bottom = size - h - top
    left = (size - w) // 2
    right = size - w - left
    return cv2.copyMakeBorder(image, top, bottom, left, right, cv2.BORDER_CONSTANT, value=colour)


# ----------------------------------------------------------------------
# Math helpers
# ----------------------------------------------------------------------

def clamp(value: float, low: float, high: float):
    """Clamp *value* into the inclusive range [low, high]."""
    return max(low, min(high, value))


def map_value(value: float, in_min: float, in_max: float, out_min: float, out_max: float):
    """Linearly map *value* from one range to another.

        Example: map_value(0.5, 0, 1, 60, 120)  ->  90
    """
    if in_max == in_min:
        raise ValueError("in_max and in_min cannot be equal – division by zero")
    ratio = (value - in_min) / (in_max - in_min)
    return out_min + ratio * (out_max - out_min)


def map_to_servo_angle(x: int, width: int, *, min_angle: int = 0, max_angle: int = 180):
    """Map horizontal pixel *x* (0‒width) to a servo angle (*min_angle*‒*max_angle*)."""
    raw = map_value(x, 0, width, min_angle, max_angle)
    return int(clamp(raw, min_angle, max_angle))


def calculate_servo_point(base_x: int, base_y: int, angle_deg: float, length: int = 200):
    """Return the end‑point of a line starting at (base_x, base_y) heading
    *angle_deg* degrees counter‑clockwise from the +X axis.  Handy for drawing
    an arrow that shows where the physical servo should be pointing.
    """
    rad = math.radians(angle_deg)
    end_x = int(base_x + length * math.cos(rad))
    end_y = int(base_y - length * math.sin(rad))  # minus because image Y grows downward
    return end_x, end_y


# ----------------------------------------------------------------------
# Quick demo when run directly (helpful in Jupyter)
# ----------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover
    print("map_to_servo_angle(x=320, width=640)  ->", map_to_servo_angle(320, 640))
    print("calculate_servo_point(100, 100, 45)   ->", calculate_servo_point(100, 100, 45))
