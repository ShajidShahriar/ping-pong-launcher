# pose_tracker.py

import cv2
import mediapipe as mp
import logging


class PoseTracker:
    def __init__(self, model_complexity=0, min_detection=0.5, min_tracking=0.5):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=model_complexity,
            smooth_landmarks=True,
            enable_segmentation=False,
            min_detection_confidence=min_detection,
            min_tracking_confidence=min_tracking
        )
        self.LEFT_HIP = self.mp_pose.PoseLandmark.LEFT_HIP
        self.RIGHT_HIP = self.mp_pose.PoseLandmark.RIGHT_HIP

    def process_frame(self, frame):
        """Returns (waist_x, waist_y) in pixels or None if no detection."""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb)
        if not results.pose_landmarks:
            return None

        h, w = frame.shape[:2]
        l = results.pose_landmarks.landmark
        x = int((l[self.LEFT_HIP].x + l[self.RIGHT_HIP].x) / 2 * w)
        y = int((l[self.LEFT_HIP].y + l[self.RIGHT_HIP].y) / 2 * h)
        self.logger.debug(f"Waist at ({x}, {y})")
        return x, y

    def close(self):
        self.pose.close()

