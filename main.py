# main.py

import cv2
import logging
from utils import make_square, calculate_servo_point
from serial_controller import SerialController
from pose_tracker import PoseTracker
from servo_aim import ServoAimer

def main():
    logging.basicConfig(level=logging.DEBUG,
                        format="%(asctime)s %(name)s %(levelname)s: %(message)s")
    # Choose mock=True for unit tests
    serial_ctrl = SerialController(port="COM5", mock=False)
    if not serial_ctrl.connect():
        return

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    tracker = PoseTracker()
    ret, frame = cap.read()
    if not ret:
        logging.error("Camera failure")
        return

    width = max(frame.shape[:2])
    aimer = ServoAimer(width=width)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = make_square(frame)
            result = tracker.process_frame(frame)
            if result:
                wx, wy = result
                angle = aimer.update(wx)
                serial_ctrl.write(f"{angle}\n")
                # visualize
                ex, ey = calculate_servo_point(width//2, width - 50, angle)
                cv2.circle(frame, (wx, wy), 5, (0,0,255), -1)
                cv2.arrowedLine(frame, (width//2, width-50), (ex, ey), (0,255,0), 5)
                cv2.putText(frame, f"Angle: {angle}", (10, 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255,0,0), 2)
            else:
                cv2.putText(frame, "No player detected", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)

            cv2.imshow("Aimer", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()
        tracker.close()
        serial_ctrl.close()

if __name__ == "__main__":
    main()

