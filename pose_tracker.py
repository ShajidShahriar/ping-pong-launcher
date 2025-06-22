"""pose_tracker.py
A very lightweight wrapper around MediaPipe Pose.  The goal is to hide the
boilerplate so `main.py` can ask one simple question:

    ok, where is the player's waist right now?

If you need extra points later (knees, shoulders, etc.) just extend
`get_landmark()` or add new helpers – the heavy lifting is already done by
MediaPipe.
"""

from __future__ import annotations

from typing import Optional, Tuple

import cv2
import mediapipe as mp

# ----------------------------------------------------------------------
# Constants – keeping them here means `main.py` stays clutter‑free
# ----------------------------------------------------------------------
MIN_DET_CONF = 0.5
MIN_TRK_CONF = 0.5
LEFT_HIP = mp.solutions.pose.PoseLandmark.LEFT_HIP
RIGHT_HIP = mp.solutions.pose.PoseLandmark.RIGHT_HIP


class PoseTracker:
    """Handles setup, frame processing and clean‑up for MediaPipe Pose."""

    def __init__(self) -> None:
        self._mp_pose = mp.solutions.pose
        self._pose = self._mp_pose.Pose(
            static_image_mode=False,
            model_complexity=0,
            smooth_landmarks=True,
            enable_segmentation=False,
            min_detection_confidence=MIN_DET_CONF,
            min_tracking_confidence=MIN_TRK_CONF,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def process(self, frame) -> Tuple[Optional[Tuple[int, int]], cv2.Mat]:
        """Run pose detection on *frame*.

        Returns (waist_xy, annotated_frame).
        *waist_xy* is (x, y) in pixel coords or None when no person is found.
        """
        # MediaPipe needs RGB, OpenCV gives BGR
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = self._pose.process(rgb)
        annotated = frame.copy()

        waist_xy: Optional[Tuple[int, int]] = None
        if res.pose_landmarks:
            # Draw the skeleton for visual feedback
            mp.solutions.drawing_utils.draw_landmarks(
                annotated,
                res.pose_landmarks,
                self._mp_pose.POSE_CONNECTIONS,
            )

            l_hip = res.pose_landmarks.landmark[LEFT_HIP]
            r_hip = res.pose_landmarks.landmark[RIGHT_HIP]
            h, w = annotated.shape[:2]
            waist_xy = (
                int((l_hip.x + r_hip.x) / 2 * w),
                int((l_hip.y + r_hip.y) / 2 * h),
            )
            cv2.circle(annotated, waist_xy, 5, (0, 0, 255), -1)

        return waist_xy, annotated

    # ------------------------------------------------------------------
    # House‑keeping
    # ------------------------------------------------------------------
    def close(self):
        """Free MediaPipe resources."""
        self._pose.close()

    # Let people use the *with* statement if they like
    def __enter__(self):  # pragma: no cover
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):  # pragma: no cover
        self.close()


# ----------------------------------------------------------------------
# Tiny smoke‑test when run directly
# ----------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise SystemExit("No webcam found.")

    with PoseTracker() as tracker:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            waist, out = tracker.process(frame)
            if waist:
                cv2.putText(out, f"waist: {waist}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.imshow("PoseTracker demo", out)
            if cv2.waitKey(1) == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()
