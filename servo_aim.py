# servo_aim.py

import time
import logging
from collections import deque
from utils import map_to_servo_angle, add_randomness


class ServoAimer:
    def __init__(
        self,
        width,
        buffer_size=5,
        stability_threshold=30,
        rand_scale=1.2,
        rand_offset=100,
        cooldown_min=15,
        cooldown_max=30
    ):
        self.width = width
        self.buffer = deque(maxlen=buffer_size)
        self.stability_threshold = stability_threshold
        self.rand_scale = rand_scale
        self.rand_offset = rand_offset
        self.cooldown_min = cooldown_min
        self.cooldown_max = cooldown_max
        self.cooldown = 0
        self.current_angle = 90
        self.logger = logging.getLogger(self.__class__.__name__)

    def update(self, waist_x):
        self.buffer.append(waist_x)
        if len(self.buffer) < self.buffer.maxlen or self.cooldown > 0:
            self.cooldown = max(0, self.cooldown - 1)
            return self.current_angle

        if max(self.buffer) - min(self.buffer) <= self.stability_threshold:
            delay = add_randomness(2, 1)  # e.g. 1–3 seconds
            self.logger.debug(f"Stable for {delay:.2f}s, aiming now")
            time.sleep(delay)

            center = self.width / 2
            delta = waist_x - center
            target_x = min(max(0, waist_x + self.rand_scale * delta + 
                               add_randomness(0, self.rand_offset)), self.width)
            base_angle = map_to_servo_angle(target_x, self.width)
            angle = add_randomness(base_angle, 20)
            angle = max(0, min(180, angle))

            self.current_angle = angle
            self.cooldown = add_randomness(self.cooldown_min, self.cooldown_max - self.cooldown_min)
            self.logger.info(f"Aimed at {angle}°, cooldown {self.cooldown}")
        return self.current_angle

