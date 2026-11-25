"""치료 세션 진행 로직 (Webots 비의존).

내담자 발화 → 대화 엔진 → 기억 갱신 → 안전 판단 → 로봇이 실행할 행동(TurnOutcome) 결정 → 로그 기록.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, asdict

from memory_model import MemoryScene
from safety import SafetyMonitor

GROUNDING_REPLY = ("네, 바로 멈출게요. 지금은 여기, 이 방에 있어요. 천천히 숨을 들이쉬고… 내쉬어 보세요. "
                   "준비되시면 언제든 말씀해 주세요.")


@dataclass
class TurnOutcome:
    reply: str
    emotion: str
    gesture: str
    phase: str
    distress: int
    safety: str
    show_scene: bool      # 기억 무대를 (다시) 그림
    clear_scene: bool     # 기억 무대를 비움
    soft: bool            # 자극 약하게
    sound: str            # 재생할 배경음 ("none" = 정지)
    scene: dict


class TherapySession:
    def __init__(self, dialogue, log_dir: str | None = None):
        self.dialogue = dialogue
        self.safety = SafetyMonitor()
        self.scene = MemoryScene()
        self.stage_active = False
        self.log_path = None
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
            self.log_path = os.path.join(log_dir, time.strftime("session_%Y%m%d_%H%M%S.jsonl"))

    def state_note(self) -> str:
        return (f"기억무대={'켜짐' if self.stage_active else '꺼짐'}, 안전단계={self.safety.level}, "
                f"현재장면={json.dumps(self.scene.snapshot(), ensure_ascii=False)}")

    def handle(self, text: str) -> TurnOutcome:
        if self.safety.is_stop_request(text):
            self.safety.force_stop()
            outcome = self._stop_outcome(GROUNDING_REPLY, distress=self.safety.history[-1] if self.safety.history else 0)
            self._log(text, outcome)
            return outcome

        result = self.dialogue.respond(text, self.state_note())
        changed = self.scene.merge(result.memory.model_dump())
        level = self.safety.update(result.distress)

        if level == "stop":
            outcome = self._stop_outcome(result.reply, result.distress)
        else:
            show = self.scene.place != "none" and (result.reenact or (self.stage_active and changed))
            if show:
                self.stage_active = True
            outcome = TurnOutcome(
                reply=result.reply, emotion=result.emotion, gesture=result.gesture, phase=result.phase,
                distress=result.distress, safety=level, show_scene=show, clear_scene=False,
                soft=level == "soft", sound=self.scene.sound if self.stage_active else "none",
                scene=self.scene.snapshot(),
            )
            if result.phase == "closure" and self.stage_active and not show:
                # 마무리 단계에서는 무대를 정리하고 현재로 돌아옴
                outcome.clear_scene, outcome.sound = True, "none"
                self.stage_active = False
        self._log(text, outcome)
        return outcome

    def _stop_outcome(self, reply: str, distress: int) -> TurnOutcome:
        self.stage_active = False
        return TurnOutcome(
            reply=reply, emotion="concerned", gesture="comfort", phase="grounding", distress=distress,
            safety="stop", show_scene=False, clear_scene=True, soft=True, sound="none",
            scene=self.scene.snapshot(),
        )

    def _log(self, text: str, outcome: TurnOutcome) -> None:
        if not self.log_path:
            return
        entry = {"t": time.time(), "engine": getattr(self.dialogue, "name", "?"), "user": text, **asdict(outcome)}
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
