from __future__ import annotations

import random
import time
from typing import Optional, Tuple

from utils import clamp, map_to_servo_angle, calculate_servo_point


class Mode:
    FOLLOW = "follow"
    RANDOM = "random"


class ServoAimer:
    def __init__(
        self,
        *,
        mode: str = Mode.FOLLOW,
        min_angle: int = 60,
        max_angle: int = 120,
        random_interval_s: Tuple[float, float] = (1.0, 3.0),
    ) -> None:
        self.mode = mode
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.random_interval_s = random_interval_s

        self.current_angle: int = (min_angle + max_angle) // 2
        self._next_random_time: float = 0.0

    # --------------------------------------------------------------
    # Public helpers
    # --------------------------------------------------------------
    def set_mode(self, mode: str) -> None:
        """Switch between Mode.FOLLOW and Mode.RANDOM."""
        self.mode = mode
        # reset timing so RANDOM fires immediately after a switch
        self._next_random_time = 0.0

    def update(self, waist_x: Optional[int], frame_width: int) -> int:
        """Return the angle for this frame."""
        now = time.time()

        # ---------------- FOLLOW ----------------
        if self.mode == Mode.FOLLOW:
            if waist_x is None:
                # lost the player -> centre
                self.current_angle = (self.min_angle + self.max_angle) // 2
            else:
                self.current_angle = map_to_servo_angle(
                    waist_x,
                    frame_width,
                    min_angle=self.min_angle,
                    max_angle=self.max_angle,
                )
            return self.current_angle

        # ---------------- RANDOM ----------------
        if self.mode == Mode.RANDOM:
            if now >= self._next_random_time:
                self.current_angle = random.randint(self.min_angle, self.max_angle)
                wait = random.uniform(*self.random_interval_s)
                self._next_random_time = now + wait
            return self.current_angle

        # fallback (should never hit)
        return self.current_angle

    # --------------------------------------------------------------
    # Drawing utility (purely visual)
    # --------------------------------------------------------------
    def draw_arrow(
        self,
        img,
        base_x: int,
        base_y: int,
        length: int = 200,
    ) -> None:
        """Draw a green arrow reflecting the current angle."""
        import cv2

        end = calculate_servo_point(base_x, base_y, self.current_angle, length)
        cv2.arrowedLine(img, (base_x, base_y), end, (0, 255, 0), 5)
        cv2.circle(img, (base_x, base_y), 8, (255, 0, 0), -1)
