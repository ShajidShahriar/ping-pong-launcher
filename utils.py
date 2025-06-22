
# utils.py

import cv2
import math
import random


def make_square(image):
    """Pad the image to a square by centering and black borders."""
    h, w = image.shape[:2]
    size = max(h, w)
    top = (size - h) // 2
    bottom = size - h - top
    left = (size - w) // 2
    right = size - w - left
    return cv2.copyMakeBorder(
        image, top, bottom, left, right, cv2.BORDER_CONSTANT, value=[0, 0, 0]
    )


def map_to_servo_angle(x, width, min_angle=0, max_angle=180):
    """Linearly map a pixel x to a servo angle between min_angle and max_angle."""
    frac = max(0.0, min(1.0, x / width))
    angle = int(min_angle + frac * (max_angle - min_angle))
    return angle


def calculate_servo_point(base_x, base_y, angle, length=200):
    """Compute end point of an arrow for visualization."""
    rad = math.radians(angle)
    return (
        int(base_x + length * math.cos(rad)),
        int(base_y - length * math.sin(rad))
    )


def add_randomness(value, amount):
    """Add plus/minus randomness within given amount."""
    return value + random.randint(-amount, amount)
