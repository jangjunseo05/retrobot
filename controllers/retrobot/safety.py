"""정서적 안전 장치.

- distress(0~10) 추세에 따라 자극 강도를 조절한다.
  normal: 정상 재현 / soft: 조명·소리 약하게 / stop: 재현 중단, 그라운딩 모드
- 내담자는 언제든 '/stop'(중단 신호)으로 즉시 멈출 수 있다.
- 실제 하드웨어로 옮길 때도 이 규칙은 LLM 판단과 별개로 로봇 쪽에서 강제한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field

SOFT_THRESHOLD = 5
STOP_THRESHOLD = 7
RECOVER_THRESHOLD = 3
RECOVER_TURNS = 2
STOP_WORDS = ("/stop", "그만", "멈춰", "중단")
# "그만" 뒤에 이 글자가 오면 중단 의사로 본다 ("그만해", "그만 할래") / "그만큼", "그만두셨어" 등은 제외
_STOP_FOLLOWERS = ("", " ", "해", "할", "하", "요", ".", "!")


@dataclass
class SafetyMonitor:
    level: str = "normal"
    history: list[int] = field(default_factory=list)
    calm_streak: int = 0

    def is_stop_request(self, text: str) -> bool:
        t = text.strip()
        if t == "/stop" or t.startswith(("멈춰", "중단")):
            return True
        return t.startswith("그만") and t[2:3] in _STOP_FOLLOWERS

    def force_stop(self) -> str:
        self.level = "stop"
        self.calm_streak = 0
        return self.level

    def update(self, distress: int) -> str:
        self.history.append(distress)
        if distress >= STOP_THRESHOLD:
            return self.force_stop()
        if self.level == "stop":
            # 충분히 안정된 상태가 연속으로 유지될 때만 해제
            self.calm_streak = self.calm_streak + 1 if distress <= RECOVER_THRESHOLD else 0
            if self.calm_streak >= RECOVER_TURNS:
                self.level = "normal"
                self.calm_streak = 0
            return self.level
        self.level = "soft" if distress >= SOFT_THRESHOLD else "normal"
        return self.level

    @property
    def allows_reenactment(self) -> bool:
        return self.level != "stop"
