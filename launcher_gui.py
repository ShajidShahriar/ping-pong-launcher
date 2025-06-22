"""
from utils import pad_square, find_camera_index

        self.mode_var = tk.StringVar(value=self.aimer.mode)
        self.spin_var = tk.StringVar(value=self.wheels._preset.name)
        self.angle_var = tk.IntVar(value=0)

        ttk.Label(frame, textvariable=self.angle_var).grid(row=0, column=2, padx=5)
        follow_btn = ttk.Button(frame, text="Follow", command=lambda: self._set_mode(Mode.FOLLOW))
        random_btn = ttk.Button(frame, text="Random", command=lambda: self._set_mode(Mode.RANDOM))
        ttk.Label(frame, textvariable=self.mode_var).grid(row=1, column=2, padx=5)
        ttk.Button(frame, text="Flat", command=lambda: self._set_spin("flat")).grid(row=2, column=0, padx=5, pady=5)
        ttk.Button(frame, text="Top Spin", command=lambda: self._set_spin("topspin")).grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(frame, text="Back Spin", command=lambda: self._set_spin("backspin")).grid(row=2, column=2, padx=5, pady=5)
        ttk.Label(frame, textvariable=self.spin_var).grid(row=2, column=3, padx=5)

    def _set_mode(self, mode: str) -> None:
        self.aimer.set_mode(mode)
        self.mode_var.set(mode)

    def _set_spin(self, preset: str) -> None:
        self.wheels.set_spin(preset)
        self.spin_var.set(preset)

        cam_idx = find_camera_index() or 0
        self.cap = cv2.VideoCapture(cam_idx)
        print(f"[GUI] Using camera {cam_idx}")

            self.angle_var.set(angle)
            cv2.putText(annotated, f"Mode:{self.aimer.mode}", (10,25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)
            cv2.putText(annotated, f"Spin:{self.wheels._preset.name}", (10,50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)
            cv2.putText(annotated, f"Ang:{angle}", (10,75), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,0), 2)
import threading
import time
import tkinter as tk
from tkinter import ttk

import cv2

from pose_tracker import PoseTracker
from servo_aim import ServoAimer, Mode
from serial_controller import SerialController
from gate_controller import GateController
from wheel_controller import WheelController
from utils import pad_square


class LauncherGUI:
    """Tk-based graphical interface for the launcher."""

    def __init__(
        self,
        *,
        port: str = "COM5",
        mock_serial: bool = True,
        cam_index: int = 1,           # ← set your working camera index here
    ) -> None:
        self.root = tk.Tk()
        self.root.title("Ping-Pong Launcher")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # ---- back-end objects ---------------------------------------
        self.serial  = SerialController(port, mock=mock_serial)
        self.serial.connect()

        self.tracker = PoseTracker()
        self.aimer   = ServoAimer(mode=Mode.FOLLOW)
        self.wheels  = WheelController(self.serial)
        self.gate    = GateController(self.serial)

        # ---- runtime state ------------------------------------------
        self.cap: cv2.VideoCapture | None = None
        self.cam_index  = cam_index
        self.running    = False
        self.loop_thread: threading.Thread | None = None

        # ---- user-tunable params ------------------------------------
        self.upper_pwm      = tk.IntVar(value=140)
        self.lower_pwm      = tk.IntVar(value=140)
        self.launch_on_time = tk.DoubleVar(value=0.3)
        self.launch_off_time = tk.DoubleVar(value=2.0)

        self._build_widgets()

    # ----------------------------------------------------------------
    # GUI layout
    # ----------------------------------------------------------------
    def _build_widgets(self) -> None:
        frame = ttk.Frame(self.root, padding=10)
        frame.grid(row=0, column=0, sticky="nsew")

        # start / stop
        ttk.Button(frame, text="Start", command=self.start).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(frame, text="Stop",  command=self.stop ).grid(row=0, column=1, padx=5, pady=5)

        # aim mode
        ttk.Button(frame, text="Follow",
                   command=lambda: (self.aimer.set_mode(Mode.FOLLOW),
                                    print("[GUI] Mode -> FOLLOW"))).grid(row=1, column=0, padx=5, pady=5)
        ttk.Button(frame, text="Random",
                   command=lambda: (self.aimer.set_mode(Mode.RANDOM),
                                    print("[GUI] Mode -> RANDOM"))).grid(row=1, column=1, padx=5, pady=5)

        # spin presets
        ttk.Button(frame, text="Flat",
                   command=lambda: (self.wheels.set_spin("flat"),
                                    print("[GUI] Spin -> FLAT"))).grid(row=2, column=0, padx=5, pady=5)
        ttk.Button(frame, text="Top Spin",
                   command=lambda: (self.wheels.set_spin("topspin"),
                                    print("[GUI] Spin -> TOP"))).grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(frame, text="Back Spin",
                   command=lambda: (self.wheels.set_spin("backspin"),
                                    print("[GUI] Spin -> BACK"))).grid(row=2, column=2, padx=5, pady=5)

        # PWM spinboxes
        ttk.Label(frame, text="Upper PWM").grid(row=3, column=0, sticky="e")
        ttk.Spinbox(frame, from_=0, to=255, textvariable=self.upper_pwm,
                    width=5, command=self._update_pwms).grid(row=3, column=1)
        ttk.Label(frame, text="Lower PWM").grid(row=4, column=0, sticky="e")
        ttk.Spinbox(frame, from_=0, to=255, textvariable=self.lower_pwm,
                    width=5, command=self._update_pwms).grid(row=4, column=1)

        # gate timing
        ttk.Label(frame, text="Gate on time (s)").grid(row=5, column=0, sticky="e")
        ttk.Spinbox(frame, from_=0.1, to=2.0, increment=0.1,
                    textvariable=self.launch_on_time, width=5).grid(row=5, column=1)
        ttk.Label(frame, text="Gate off time (s)").grid(row=6, column=0, sticky="e")
        ttk.Spinbox(frame, from_=0.1, to=5.0, increment=0.1,
                    textvariable=self.launch_off_time, width=5).grid(row=6, column=1)

    # ----------------------------------------------------------------
    # Button callbacks
    # ----------------------------------------------------------------
    def _update_pwms(self) -> None:
        self.wheels.set_base_pwms(self.upper_pwm.get(), self.lower_pwm.get())

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.loop_thread = threading.Thread(target=self._loop, daemon=True)
        self.loop_thread.start()

    def stop(self) -> None:
        self.running = False
        if self.loop_thread:
            self.loop_thread.join(timeout=1.0)
            self.loop_thread = None

    def _on_close(self) -> None:
        self.stop()
        self.root.destroy()

    # ----------------------------------------------------------------
    # Frame loop
    # ----------------------------------------------------------------
    def _loop(self) -> None:
        self.cap = cv2.VideoCapture(self.cam_index)
        if not self.cap.isOpened():
            print("[GUI] Cannot open camera.")
            self.running = False
            return

        last_launch = time.time()
        while self.running:
            ok, frame = self.cap.read()
            if not ok:
                break

            frame = pad_square(frame)
            waist_xy, annotated = self.tracker.process(frame)

            # ----- aim + arrow --------------------------------------
            angle = self.aimer.update(waist_xy[0] if waist_xy else None,
                                      annotated.shape[1])
            self.serial.write_angle(angle)
            self.aimer.draw_arrow(annotated,
                                  annotated.shape[1] // 2,
                                  annotated.shape[0] - 40)

            cv2.imshow("Launcher", annotated)
            if cv2.waitKey(1) == 27:         # ESC closes
                self.stop()
                break

            # ----- timed launch routine -----------------------------
            now = time.time()
            if now - last_launch >= self.launch_off_time.get():
                self.wheels.fire()
                self.gate.open()
                time.sleep(self.launch_on_time.get())
                self.gate.close()
                last_launch = time.time()

        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()

    # ----------------------------------------------------------------
    def run(self) -> None:
        self.root.mainloop()


def main() -> None:          # convenient entry-point
    LauncherGUI().run()


if __name__ == "__main__":
    main()
