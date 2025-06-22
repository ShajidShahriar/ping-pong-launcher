"""
main.py
=======

q         : quit
m         : toggle aim FOLLOW/RANDOM
(space)   : launch ball          [only when --spin flag is used]
t / b / f : topspin / backspin / flat shot presets  [only with --spin]

Run without flags for plain tracking + servo.
Add --spin to enable wheel controls.
Use --gui  to start the Tkinter interface instead of the CLI demo.
Use --port to specify the Arduino serial port.
Use --[no-]mock to enable or disable mock serial mode.
"""

from __future__ import annotations
import argparse, time
import cv2

from pose_tracker import PoseTracker
from servo_aim import ServoAimer, Mode
from serial_controller import SerialController
from gate_controller import GateController
from utils import pad_square, find_camera_index
from collections import deque

# ------------------------------------------------ Argument flag
parser = argparse.ArgumentParser()
parser.add_argument(
    "--spin",
    action="store_true",
    help="enable dual-wheel spin control (top/back/flat)",
)
parser.add_argument(
    "--gui",
    action="store_true",
    help="launch the Tkinter GUI",
)
parser.add_argument(
    "--port",
    default="COM5",
    help="serial port for the Arduino",
)
parser.add_argument(
    "--mock",
    action=argparse.BooleanOptionalAction,
    default=True,
    help="use a mock serial connection",
)
args = parser.parse_args()

# ------------------------------------------------ Config
WEBCAM_INDEX = find_camera_index() or 0
FRAME_W, FRAME_H, FPS = 640, 480, 30
WINDOW_NAME  = "Ping-Pong Servo Aimer"

# ------------------------------------------------ Main
def main() -> None:
    if args.gui:
        from launcher_gui import LauncherGUI
        gui = LauncherGUI(port=args.port, mock_serial=args.mock)
        gui.run()
        return

    ser = SerialController(args.port, mock=args.mock)
    ser.connect()

    # optional wheel controller
    if args.spin:
        from wheel_controller import WheelController  # local import keeps deps optional
        wheels = WheelController(ser, preset="flat")
        gate = GateController(ser)

    cap = cv2.VideoCapture(WEBCAM_INDEX)
    if not cap.isOpened():
        print("[Main] Cannot open camera.")
        return
    print(f"[Main] Using camera {WEBCAM_INDEX}")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)
    cap.set(cv2.CAP_PROP_FPS, FPS)

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, FRAME_W, FRAME_W)

    tracker = PoseTracker()
    aimer   = ServoAimer(mode=Mode.FOLLOW)
    angle_buffer = deque(maxlen=5)

    print("[Main] q=quit  m=mode", end="")
    if args.spin:
        print("  t/b/f=spin  space=fire")
    else:
        print("  (run with --spin to enable wheel control)")

    prev = time.time()
    while True:
        ok, frame = cap.read()
        if not ok:
            break

        frame = pad_square(frame)
        h, w = frame.shape[:2]

        waist_xy, annotated = tracker.process(frame)
        waist_x = waist_xy[0] if waist_xy else None
        angle   = aimer.update(waist_x, w)
        ser.write_angle(angle)
        angle_buffer.append(angle)

        aimer.draw_arrow(annotated, w // 2, h - 40)

        # HUD
        fps = 1 / (time.time() - prev); prev = time.time()
        cv2.putText(annotated, f"Aim:{angle}", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, .7, (255, 255, 0), 2)
        cv2.putText(annotated, f"FPS:{int(fps)}", (10, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, .7, (255, 255, 0), 2)
        cv2.putText(annotated, f"Mode:{aimer.mode}", (10, 75),
                    cv2.FONT_HERSHEY_SIMPLEX, .7, (200, 255, 0), 2)
        if args.spin:
            cv2.putText(annotated, f"Spin:{wheels._preset.name}", (10, 100),
                        cv2.FONT_HERSHEY_SIMPLEX, .7, (200, 255, 0), 2)

        cv2.imshow(WINDOW_NAME, annotated)
        key = cv2.waitKey(1) & 0xFF

        if   key == ord("q"):
            break
        elif key == ord("m"):
            new = Mode.RANDOM if aimer.mode == Mode.FOLLOW else Mode.FOLLOW
            aimer.set_mode(new)
            print("[Main] Aim :", new)

        # ---------------- wheel hotkeys (only active with --spin)
        elif args.spin:
            if   key == ord("t"):
                wheels.set_spin("topspin");  print("[Main] Topspin armed")
            elif key == ord("b"):
                wheels.set_spin("backspin"); print("[Main] Backspin armed")
            elif key == ord("f"):
                wheels.set_spin("flat");     print("[Main] Flat shot armed")
            elif key == ord(" "):
                if len(angle_buffer) == angle_buffer.maxlen and len(set(angle_buffer)) == 1:
                    wheels.fire()
                    gate.open()
                    time.sleep(0.3)
                    gate.close()
                    print("[Main] FIRE!")
                else:
                    print("[Main] Hold steady to fire")

    # tidy-up
    cap.release(); cv2.destroyAllWindows()
    tracker.close(); ser.close()

if __name__ == "__main__":
    main()
