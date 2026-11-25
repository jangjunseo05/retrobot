"""기억 속 소리 재생 (Webots Speaker)."""
from __future__ import annotations

import os

from controller import Speaker

SOUND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets", "sounds")
BEEP = "beep"


class Audio:
    def __init__(self, robot):
        self.speaker = robot.getDevice("speaker")
        self.current: str | None = None

    def _path(self, name: str) -> str:
        return os.path.normpath(os.path.join(SOUND_DIR, f"{name}.wav"))

    def play_ambient(self, name: str, volume: float = 0.6) -> None:
        if name in (None, "none"):
            self.stop_ambient()
            return
        path = self._path(name)
        if not os.path.exists(path):
            print(f"[retrobot] 소리 파일 없음: {path}  (python tools/gen_sounds.py 실행)")
            return
        if self.current == path:
            return
        self.stop_ambient()
        Speaker.playSound(self.speaker, self.speaker, path, volume, 1.0, 0.0, True)
        self.current = path

    def stop_ambient(self) -> None:
        if self.current:
            self.speaker.stop(self.current)
            self.current = None

    def beep(self) -> None:
        path = self._path(BEEP)
        if os.path.exists(path):
            Speaker.playSound(self.speaker, self.speaker, path, 0.4, 1.0, 0.0, False)
