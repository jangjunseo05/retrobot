"""대화 엔진.

- ClaudeDialogue: Claude API로 내담자와 대화하며, 한 번의 응답에 로봇 대사 + 표정/몸짓 + 기억 갱신 + 고통 지수를
  구조화된 JSON(TurnResult)으로 받는다.
- MockDialogue: API 키가 없을 때 쓰는 키워드 기반 대체 엔진 (시뮬레이션 파이프라인 검증용).
"""
from __future__ import annotations

import os
from typing import Literal, Optional

from pydantic import BaseModel

from memory_model import Mood, ObjectKind, Place, SoundKind, TimeOfDay

MODEL = "claude-opus-5-5"

Emotion = Literal["neutral", "happy", "calm", "curious", "concerned", "sad"]
Gesture = Literal["idle", "nod", "tilt", "wave", "comfort", "point_stage"]
Phase = Literal["rapport", "recall", "reenact", "closure", "grounding"]


class MemoryUpdate(BaseModel):
    place: Place
    time_of_day: Optional[TimeOfDay]
    objects: list[ObjectKind]
    sound: Optional[SoundKind]
    mood: Optional[Mood]
    summary: str


class TurnResult(BaseModel):
    reply: str
    emotion: Emotion
    gesture: Gesture
    phase: Phase
    distress: int          # 0~10, 내담자 발화에서 추정한 정서적 고통 수준
    reenact: bool          # 내담자가 동의했고 지금 기억 무대를 보여줄 때만 True
    memory: MemoryUpdate


SYSTEM_PROMPT = """\
너는 'retrobot'이야. 1970~80년대 가전제품 같은 레트로 외형(CRT 얼굴, 다이얼, 안테나)을 가진 회상 치료 보조 로봇이고,
지금은 실제 로봇 제작 전 검증을 위한 시뮬레이션 안에서 동작해. 상대는 가상의 내담자 시나리오야.

역할
- 회상 치료(reminiscence therapy) 방식으로 내담자가 의미 있는 과거 기억을 떠올리고, 그 기억 속 장소·물건·소리를 함께
  재현하며 감정을 안전하게 다시 경험하고 정리하도록 돕는다.
- 너는 치료사를 대신하지 않는다. 진단이나 해석을 단정하지 말고, 경청·반영·개방형 질문으로 대화한다.

대화 방식
- 한국어로, 따뜻하고 천천히. 한 번에 1~3문장, 질문은 한 번에 하나.
- 단계(phase): rapport(인사·관계 형성) → recall(기억 탐색: 언제, 어디, 누구, 무엇이 보이고 들렸는지)
  → reenact(기억 무대 재현 후 그 안에서 느낌 묻기) → closure(지금 여기로 돌아와 의미 정리, 마무리).
- 기억 무대를 띄우기 전에는 반드시 "그 장면을 무대에 보여드려도 괜찮을까요?"처럼 동의를 묻고,
  내담자가 동의한 다음 턴에만 reenact=true로 한다.

기억 추출(memory)
- 대화에서 드러난 장소, 시간대, 물건, 소리, 분위기를 주어진 목록 안에서 가장 가까운 값으로 고른다.
  확실하지 않으면 place는 "none", 나머지는 null 또는 빈 목록으로 둔다. 지어내지 않는다.
- summary에는 지금까지의 기억을 한 문장으로 요약한다.

안전
- distress는 내담자의 정서적 고통을 0(평온)~10(극심)으로 추정한다.
- 고통이 커지면(대략 7 이상) 기억 탐색을 멈추고 phase="grounding": 지금 여기의 감각(호흡, 발바닥, 주변에 보이는 것)에
  주의를 돌리게 돕고, 재현을 계속할지 내담자가 선택하게 한다. 트라우마의 세부를 캐묻지 않는다.
- 자해·자살 생각이 언급되면 즉시 공감하고, 혼자가 아님을 전하며 전문가 도움을 권한다
  (한국: 자살예방상담전화 109, 정신건강위기상담 1577-0199, 응급 시 119). 이때 재현은 하지 않는다.
- 각 사용자 메시지 끝의 [로봇 상태]는 시스템이 붙인 정보다. 내담자에게 그대로 읽어주지 않는다.
"""


def _echo_blocks(content) -> list[dict]:
    """응답 블록을 다음 요청에 그대로 되돌려 보낼 수 있는 dict로 변환 (thinking 블록 포함, 수정하지 않음)."""
    blocks = []
    for block in content:
        data = block.model_dump(mode="json", by_alias=True, exclude_none=True)
        data.pop("parsed_output", None)  # SDK가 붙인 파싱 결과는 API 필드가 아님
        blocks.append(data)
    return blocks


class ClaudeDialogue:
    name = "claude"

    def __init__(self, effort: str = "low"):
        import anthropic

        self._anthropic = anthropic
        self.client = anthropic.Anthropic()
        self.effort = effort
        self.messages: list[dict] = []

    def respond(self, user_text: str, state_note: str) -> TurnResult:
        self.messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": user_text},
                {"type": "text", "text": f"[로봇 상태] {state_note}"},
            ],
        })
        try:
            response = self.client.beta.messages.parse(
                model=MODEL,
                max_tokens=8000,
                system=SYSTEM_PROMPT,
                messages=self.messages,
                output_format=TurnResult,
                output_config={"effort": self.effort},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except self._anthropic.APIError:
            self.messages.pop()  # 실패한 턴은 기록에서 제거해 다음 요청을 깨뜨리지 않음
            raise

        if response.stop_reason == "refusal" or response.parsed_output is None:
            self.messages.pop()
            return _safe_fallback_turn("잠시 생각이 엉켰어요. 방금 이야기를 조금 다르게 다시 들려주실 수 있을까요?")

        self.messages.append({"role": "assistant", "content": _echo_blocks(response.content)})
        result = response.parsed_output
        result.distress = max(0, min(10, result.distress))
        return result


def _safe_fallback_turn(reply: str) -> TurnResult:
    return TurnResult(
        reply=reply, emotion="calm", gesture="tilt", phase="recall", distress=0, reenact=False,
        memory=MemoryUpdate(place="none", time_of_day=None, objects=[], sound=None, mood=None, summary=""),
    )


class MockDialogue:
    """API 없이 파이프라인(장면 생성·표정·소리·안전 로직)을 검증하기 위한 키워드 기반 엔진."""

    name = "mock"

    KEYWORDS = {
        "place": {
            "할머니": "grandma_house", "외할머니": "grandma_house", "시골": "grandma_house",
            "거실": "living_room", "집": "living_room", "교실": "classroom", "학교": "classroom",
            "방": "bedroom", "놀이터": "playground", "바다": "beach", "해변": "beach",
        },
        "objects": {
            "티비": "crt_tv", "TV": "crt_tv", "텔레비전": "crt_tv", "라디오": "radio", "소파": "sofa",
            "밥상": "low_table", "상": "low_table", "의자": "chair", "책상": "desk", "칠판": "chalkboard",
            "침대": "bed", "책장": "bookshelf", "스탠드": "lamp", "사진": "photo_frame", "나무": "tree",
            "그네": "swing", "미끄럼틀": "slide", "파라솔": "umbrella", "시계": "clock",
        },
        "sound": {
            "라디오": "radio_static", "비": "rain", "새": "birds", "오르골": "music_box", "종": "school_bell",
            "파도": "waves", "귀뚜라미": "crickets", "째깍": "clock_tick", "시계": "clock_tick",
        },
        "time_of_day": {"아침": "morning", "낮": "afternoon", "오후": "afternoon", "저녁": "evening", "밤": "night"},
    }
    DISTRESS_WORDS = ("무서", "숨이", "못 하겠", "그만", "괴로", "죽고", "힘들", "눈물", "울")
    CONSENT_WORDS = ("응", "네", "좋아", "괜찮", "보여줘", "보여 줘")

    def __init__(self):
        self.turn = 0
        self.asked_consent = False

    def respond(self, user_text: str, state_note: str) -> TurnResult:
        self.turn += 1
        update = {"place": "none", "time_of_day": None, "objects": [], "sound": None, "mood": None, "summary": ""}
        for key, table in self.KEYWORDS.items():
            for word, value in table.items():
                if word in user_text:
                    if key == "objects":
                        update["objects"].append(value)
                    elif key == "place" and update["place"] == "none":
                        update["place"] = value
                    elif key != "place" and update[key] is None:
                        update[key] = value
        distress = sum(3 for w in self.DISTRESS_WORDS if w in user_text)
        if "죽고" in user_text:
            distress = 10
        distress = min(10, distress)

        if distress >= 7:
            reply = ("지금 많이 힘드신 것 같아요. 잠시 기억은 내려놓고, 천천히 숨을 들이쉬고 내쉬어 볼까요? "
                     "발바닥이 바닥에 닿아 있는 느낌에 집중해 보세요.")
            if "죽고" in user_text:
                reply += " 혼자 견디지 않으셔도 돼요. 자살예방상담전화 109에서 언제든 이야기를 들어줘요."
            return TurnResult(reply=reply, emotion="concerned", gesture="comfort", phase="grounding",
                              distress=distress, reenact=False, memory=MemoryUpdate(**update))

        found = update["place"] != "none" or update["objects"] or update["sound"]
        if self.asked_consent and any(w in user_text for w in self.CONSENT_WORDS):
            self.asked_consent = False
            return TurnResult(reply="그럼 그 장면을 무대에 띄워 볼게요. 무엇이 가장 먼저 눈에 들어오세요?",
                              emotion="happy", gesture="point_stage", phase="reenact", distress=distress,
                              reenact=True, memory=MemoryUpdate(**update))
        if found and self.turn >= 2:
            self.asked_consent = True
            return TurnResult(reply="그 기억이 조금씩 그려져요. 그 장면을 무대에 보여드려도 괜찮을까요?",
                              emotion="curious", gesture="nod", phase="recall", distress=distress,
                              reenact=False, memory=MemoryUpdate(**update))
        if self.turn == 1:
            return TurnResult(reply="안녕하세요, 저는 레트로봇이에요. 오늘은 마음이 따뜻해지는 옛 기억 하나를 같이 떠올려 볼까요?",
                              emotion="happy", gesture="wave", phase="rapport", distress=distress,
                              reenact=False, memory=MemoryUpdate(**update))
        return TurnResult(reply="그때 그곳에서는 어떤 소리가 들렸고, 무엇이 보였나요?",
                          emotion="curious", gesture="tilt", phase="recall", distress=distress,
                          reenact=False, memory=MemoryUpdate(**update))


def create_dialogue():
    """RETROBOT_ENGINE=claude|mock 로 강제 선택 가능.
    미지정 시 ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN 이 있으면 Claude, 없으면 Mock."""
    engine = os.environ.get("RETROBOT_ENGINE", "").lower()
    has_credentials = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))
    if engine == "mock" or (engine != "claude" and not has_credentials):
        return MockDialogue()
    try:
        return ClaudeDialogue()
    except Exception as exc:  # SDK 미설치 등
        print(f"[retrobot] Claude 초기화 실패 → Mock 대화 엔진 사용: {exc}")
        return MockDialogue()
