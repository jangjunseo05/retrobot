"""표정(CRT 얼굴) · 몸짓(고개/팔) · 안테나 LED 제어."""
from __future__ import annotations

import math

PHOSPHOR = 0x33FF66   # 녹색 인광 CRT
DIM = 0x0B3D1A
BG = 0x020A04

LED_COLORS = {
    "neutral": 0x40A0FF, "happy": 0xFFC040, "calm": 0x40FFB0,
    "curious": 0xC080FF, "concerned": 0xFF8040, "sad": 0x4060C0,
}

# 몸짓 키프레임: (시간[s], {모터: 각도[rad]})
GESTURES = {
    "idle": [(0.0, {"neck_pan": 0.0, "neck_tilt": 0.0, "left_shoulder": 0.0, "right_shoulder": 0.0})],
    "nod": [(0.0, {"neck_tilt": 0.0}), (0.3, {"neck_tilt": 0.3}), (0.6, {"neck_tilt": -0.05}),
            (0.9, {"neck_tilt": 0.25}), (1.2, {"neck_tilt": 0.0})],
    "tilt": [(0.0, {"neck_pan": 0.0}), (0.5, {"neck_pan": 0.25, "neck_tilt": -0.1}),
             (1.8, {"neck_pan": 0.25, "neck_tilt": -0.1}), (2.3, {"neck_pan": 0.0, "neck_tilt": 0.0})],
    "wave": [(0.0, {"right_shoulder": 0.0}), (0.4, {"right_shoulder": -2.3}), (0.7, {"right_shoulder": -1.9}),
             (1.0, {"right_shoulder": -2.3}), (1.3, {"right_shoulder": -1.9}), (1.8, {"right_shoulder": 0.0})],
    "comfort": [(0.0, {"left_shoulder": 0.0, "right_shoulder": 0.0, "neck_tilt": 0.0}),
                (0.8, {"left_shoulder": -0.7, "right_shoulder": -0.7, "neck_tilt": 0.2}),
                (3.0, {"left_shoulder": -0.7, "right_shoulder": -0.7, "neck_tilt": 0.2}),
                (3.8, {"left_shoulder": 0.0, "right_shoulder": 0.0, "neck_tilt": 0.0})],
    # 무대(-Y 방향)를 가리키고 바라봄
    "point_stage": [(0.0, {"neck_pan": 0.0, "right_shoulder": 0.0}),
                    (0.8, {"neck_pan": -0.9, "right_shoulder": -1.5}),
                    (3.0, {"neck_pan": -0.9, "right_shoulder": -1.5}),
                    (3.8, {"neck_pan": 0.0, "right_shoulder": 0.0})],
}
MOTORS = ("neck_pan", "neck_tilt", "left_shoulder", "right_shoulder")


class Expression:
    def __init__(self, robot):
        self.display = robot.getDevice("face")
        self.led = robot.getDevice("antenna_led")
        self.motors = {name: robot.getDevice(name) for name in MOTORS}
        for motor in self.motors.values():
            motor.setVelocity(2.0)
        self.w = self.display.getWidth()
        self.h = self.display.getHeight()
        self.emotion = "neutral"
        self.talking_until = 0.0
        self.gesture = GESTURES["idle"]
        self.gesture_start = 0.0
        self.pose = {name: 0.0 for name in MOTORS}

    # ---------------- 상태 설정 ----------------
    def set_emotion(self, emotion: str) -> None:
        self.emotion = emotion if emotion in LED_COLORS else "neutral"
        self.led.set(LED_COLORS[self.emotion])

    def play_gesture(self, name: str, now: float) -> None:
        self.gesture = GESTURES.get(name, GESTURES["idle"])
        self.gesture_start = now

    def talk(self, text: str, now: float) -> None:
        self.talking_until = now + min(8.0, 0.08 * len(text))  # 글자 수에 비례해 입 움직임

    # ---------------- 매 스텝 갱신 ----------------
    def update(self, now: float) -> None:
        self._update_motors(now - self.gesture_start)
        self._draw_face(now)

    def _update_motors(self, t: float) -> None:
        frames = self.gesture
        for name in MOTORS:
            keys = [(ft, pose[name]) for ft, pose in frames if name in pose]
            if not keys:
                continue
            if t <= keys[0][0]:
                target = keys[0][1]
            elif t >= keys[-1][0]:
                target = keys[-1][1]
            else:
                for (t0, a0), (t1, a1) in zip(keys, keys[1:]):
                    if t0 <= t <= t1:
                        target = a0 + (a1 - a0) * (t - t0) / (t1 - t0)
                        break
            if abs(target - self.pose[name]) > 1e-3:
                self.pose[name] = target
                self.motors[name].setPosition(target)

    def _draw_face(self, now: float) -> None:
        d, w, h = self.display, self.w, self.h
        d.setColor(BG)
        d.fillRectangle(0, 0, w, h)

        blink = (now % 4.0) < 0.12
        eye_y, eye_dx, rx, ry = int(h * 0.4), int(w * 0.22), int(w * 0.1), int(h * 0.13)
        d.setColor(PHOSPHOR)
        for side in (-1, 1):
            cx = w // 2 + side * eye_dx
            if blink:
                d.fillRectangle(cx - rx, eye_y, 2 * rx, 3)
            elif self.emotion == "happy":       # ^ ^
                d.drawLine(cx - rx, eye_y + 4, cx, eye_y - ry // 2)
                d.drawLine(cx, eye_y - ry // 2, cx + rx, eye_y + 4)
            elif self.emotion == "calm":        # 반쯤 감은 눈
                d.fillRectangle(cx - rx, eye_y, 2 * rx, ry // 2)
            elif self.emotion == "sad":         # 처진 눈썹 + 작은 눈
                d.fillOval(cx, eye_y + 3, rx // 2, ry // 2)
                d.drawLine(cx - rx, eye_y - ry + side * -4, cx + rx, eye_y - ry + side * 4)
            elif self.emotion == "concerned":
                d.fillOval(cx, eye_y, rx // 2 + 2, ry // 2 + 2)
                d.drawLine(cx - rx, eye_y - ry + side * 4, cx + rx, eye_y - ry - side * 4)
            elif self.emotion == "curious":     # 한쪽 눈 크게
                scale = 1.0 if side < 0 else 0.7
                d.fillOval(cx, eye_y, int(rx * 0.7 * scale), int(ry * scale))
            else:
                d.fillOval(cx, eye_y, int(rx * 0.7), ry)

        mouth_y, mw = int(h * 0.75), int(w * 0.18)
        cx = w // 2
        if now < self.talking_until:
            opening = int(3 + 5 * abs(math.sin(now * 14)))
            d.fillOval(cx, mouth_y, mw // 2, opening)
        elif self.emotion in ("happy", "calm"):
            self._arc(cx, mouth_y - 6, mw, 8, smile=True)
        elif self.emotion in ("sad", "concerned"):
            self._arc(cx, mouth_y + 4, mw, 6, smile=False)
        else:
            d.fillRectangle(cx - mw // 2, mouth_y, mw, 3)

        # CRT 주사선
        d.setColor(DIM)
        for y in range(0, h, 3):
            d.drawLine(0, y, w, y)

    def _arc(self, cx: int, cy: int, width: int, depth: int, smile: bool) -> None:
        sign = 1 if smile else -1
        pts = []
        for i in range(11):
            x = -width / 2 + width * i / 10
            pts.append((int(cx + x), int(cy + sign * depth * (1 - (2 * x / width) ** 2))))
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            self.display.drawLine(x0, y0, x1, y1)
            self.display.drawLine(x0, y0 + 1, x1, y1 + 1)
