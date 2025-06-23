"""
Simple Tkinter GUI for the ping‑pong launcher.

Start  → begin pose tracking / angle streaming  
Stop   → halt video thread and release the webcam  
Follow / Random → aim modes  
Flat / Top Spin / Back Spin → wheel presets
"""

from __future__ import annotations

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
from utils import pad_square, find_camera_index, find_serial_port



class LauncherGUI:
    """Tk‑based graphical interface for the launcher."""

    def __init__(
        self,
        *,
        port: str = "COM5",
        mock_serial: bool = True,
        cam_index: int | None = None,       # None → auto‑detect
    ) -> None:
        """Initialize the interface.

        Parameters
        ----------
        port:
            Serial port for the Arduino.
        mock_serial:
            If ``True`` use a mock serial connection. This can also be
            toggled later from the GUI.
        cam_index:
            Webcam index or ``None`` to auto‑detect. Defaults to ``None``.
        """
        # -------- tkinter window --------
        self.root = tk.Tk()
        self.root.title("Ping‑Pong Launcher")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # -------- back‑end objects ------
        if port is None:
            port = find_serial_port() or "COM5"
        self.serial = SerialController(port, mock=mock_serial)
        self.serial.connect()

        self.tracker = PoseTracker()
        self.aimer   = ServoAimer(mode=Mode.FOLLOW)
        self.wheels  = WheelController(self.serial)
        self.gate    = GateController(self.serial)

        # -------- runtime state ---------
        self.cam_index = cam_index
        self.cap: cv2.VideoCapture | None = None
        self.running   = False
        self.loop_thread: threading.Thread | None = None

        # -------- user‑tunable params ---
        self.upper_pwm       = tk.IntVar(value=140)
        self.lower_pwm       = tk.IntVar(value=140)
        self.launch_on_time  = tk.DoubleVar(value=0.3)
        self.launch_off_time = tk.DoubleVar(value=2.0)

        # UI feedback vars
        self.mode_var  = tk.StringVar(value=str(self.aimer.mode))
        self.spin_var  = tk.StringVar(value=self.wheels._preset.name)
        self.angle_var = tk.IntVar(value=0)
        self.mock_var  = tk.BooleanVar(value=mock_serial)

        self._build_widgets()

    # ------------------------------------------------------------------
    # GUI layout
    # ------------------------------------------------------------------
    def _build_widgets(self) -> None:
        frame = ttk.Frame(self.root, padding=10)
        frame.grid(row=0, column=0, sticky="nsew")

        # --- start / stop ------------------------------------------------
        self.start_btn = ttk.Button(frame, text="Start", command=self.start)
        self.start_btn.grid(row=0, column=0, padx=5, pady=5)
        self.stop_btn = ttk.Button(frame, text="Stop", command=self.stop)
        self.stop_btn.grid(row=0, column=1, padx=5, pady=5)
        self.stop_btn.state(["disabled"])
        ttk.Label(frame, textvariable=self.angle_var).grid(row=0, column=2, padx=5)

        # --- aim mode ----------------------------------------------------
        ttk.Button(frame, text="Follow",
                   command=lambda: self._set_mode(Mode.FOLLOW)).grid(row=1, column=0, padx=5, pady=5)
        ttk.Button(frame, text="Random",
                   command=lambda: self._set_mode(Mode.RANDOM)).grid(row=1, column=1, padx=5, pady=5)
        ttk.Label(frame, textvariable=self.mode_var).grid(row=1, column=2, padx=5)

        # --- spin presets ------------------------------------------------
        ttk.Button(frame, text="Flat",
                   command=lambda: self._set_spin("flat")).grid(row=2, column=0, padx=5, pady=5)
        ttk.Button(frame, text="Top Spin",
                   command=lambda: self._set_spin("topspin")).grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(frame, text="Back Spin",
                   command=lambda: self._set_spin("backspin")).grid(row=2, column=2, padx=5, pady=5)
        ttk.Label(frame, textvariable=self.spin_var).grid(row=2, column=3, padx=5)

        # --- PWM spinboxes -----------------------------------------------
        ttk.Label(frame, text="Upper PWM").grid(row=3, column=0, sticky="e")
        ttk.Spinbox(frame, from_=0, to=255, textvariable=self.upper_pwm,
                    width=5, command=self._update_pwms).grid(row=3, column=1)
        ttk.Label(frame, text="Lower PWM").grid(row=4, column=0, sticky="e")
        ttk.Spinbox(frame, from_=0, to=255, textvariable=self.lower_pwm,
                    width=5, command=self._update_pwms).grid(row=4, column=1)

        # --- gate timing -------------------------------------------------
        ttk.Label(frame, text="Gate on time (s)").grid(row=5, column=0, sticky="e")
        ttk.Spinbox(frame, from_=0.1, to=2.0, increment=0.1,
                    textvariable=self.launch_on_time, width=5).grid(row=5, column=1)
        ttk.Label(frame, text="Gate off time (s)").grid(row=6, column=0, sticky="e")
        ttk.Spinbox(frame, from_=0.1, to=5.0, increment=0.1,
                    textvariable=self.launch_off_time, width=5).grid(row=6, column=1)

        # --- serial mode toggle -------------------------------------------
        ttk.Checkbutton(
            frame,
            text="Mock Serial",
            variable=self.mock_var,
            command=self._toggle_mock,
        ).grid(row=7, column=0, columnspan=2, sticky="w")

    # ------------------------------------------------------------------
    # Button callbacks
    # ------------------------------------------------------------------
    def _update_pwms(self) -> None:
        self.wheels.set_base_pwms(self.upper_pwm.get(), self.lower_pwm.get())

    def _set_mode(self, mode: Mode) -> None:
        self.aimer.set_mode(mode)
        self.mode_var.set(str(mode))
        print(f"[GUI] Mode -> {mode}")

    def _set_spin(self, preset: str) -> None:
        self.wheels.set_spin(preset)
        self.spin_var.set(preset)
        print(f"[GUI] Spin -> {preset.upper()}")

    def _toggle_mock(self) -> None:
        """Callback to switch between mock and real serial mode."""
        use_mock = self.mock_var.get()
        self.serial.set_mock(use_mock)
        state = "MOCK" if use_mock else "REAL"
        print(f"[GUI] Serial mode -> {state}")

    # ------------------------------------------------------------------
    # Lifecycle controls
    # ------------------------------------------------------------------
    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.start_btn.state(["disabled"])
        self.stop_btn.state(["!disabled"])
        self.loop_thread = threading.Thread(target=self._loop, daemon=True)
        self.loop_thread.start()

    def stop(self) -> None:
        self.running = False
        self.start_btn.state(["!disabled"])
        self.stop_btn.state(["disabled"])
        if self.loop_thread and threading.current_thread() is not self.loop_thread:
            self.loop_thread.join(timeout=1.0)
            self.loop_thread = None

    def _on_close(self) -> None:
        self.stop()
        self.root.destroy()

    # ------------------------------------------------------------------
    # Video / pose loop (runs in background thread)
    # ------------------------------------------------------------------
    def _loop(self) -> None:
        # camera selection
        cam = self.cam_index if self.cam_index is not None else (find_camera_index() or 0)
        self.cap = cv2.VideoCapture(cam)
        if not self.cap.isOpened():
            print("[GUI] Cannot open camera.")
            self.running = False
            return
        print(f"[GUI] Using camera {cam}")

        window_name = "Launcher Preview"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

        last_launch = time.time()

        while self.running:
            ok, frame = self.cap.read()
            if not ok:
                break

            frame = pad_square(frame)
            waist_xy, annotated = self.tracker.process(frame)

            # ------- aim + arrow ------------------------------------
            angle = self.aimer.update(
                waist_xy[0] if waist_xy else None,
                annotated.shape[1],
            )
            self.serial.write_angle(angle)
            self.angle_var.set(angle)
            self.aimer.draw_arrow(
                annotated,
                annotated.shape[1] // 2,
                annotated.shape[0] - 40,
            )

            # HUD overlays
            cv2.putText(annotated, f"Mode:{self.aimer.mode}", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            cv2.putText(annotated, f"Spin:{self.wheels._preset.name}", (10, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            cv2.putText(annotated, f"Ang:{angle}", (10, 75),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

            cv2.imshow(window_name, annotated)
            cv2.waitKey(1)

            # ------- timed launch routine ---------------------------
            now = time.time()
            if now - last_launch >= self.launch_off_time.get():
                self.wheels.fire()
                self.gate.open()
                time.sleep(self.launch_on_time.get())
                self.gate.close()
                last_launch = time.time()

        # Cleanup ----------------------------------------------------
        if self.cap:
            self.cap.release()
        cv2.destroyWindow(window_name)
        self.loop_thread = None

    # ------------------------------------------------------------------
    def run(self) -> None:
        """Start the Tkinter main‑loop."""
        self.root.mainloop()


# Convenience entry‑point

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", help="Arduino serial port; auto‑detect if omitted")
    args = parser.parse_args()

    LauncherGUI(port=args.port).run()


if __name__ == "__main__":
    main()
