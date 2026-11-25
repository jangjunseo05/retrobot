"""기억 데이터 모델.

대화에서 추출한 기억 조각(장소, 시간대, 물건, 소리, 분위기)을 하나의 장면(MemoryScene)으로 누적한다.
Webots에 의존하지 않으므로 단독 테스트가 가능하다.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Literal, get_args

Place = Literal[
    "none", "living_room", "grandma_house", "classroom", "bedroom", "playground", "beach",
]
TimeOfDay = Literal["morning", "afternoon", "evening", "night"]
ObjectKind = Literal[
    "crt_tv", "radio", "sofa", "low_table", "chair", "desk", "chalkboard", "bed",
    "bookshelf", "lamp", "photo_frame", "tree", "swing", "slide", "umbrella", "clock",
]
SoundKind = Literal[
    "none", "radio_static", "rain", "birds", "music_box", "school_bell", "waves", "crickets", "clock_tick",
]
Mood = Literal["warm", "nostalgic", "calm", "lonely", "tense", "joyful"]

PLACES: tuple[str, ...] = get_args(Place)
TIMES: tuple[str, ...] = get_args(TimeOfDay)
OBJECTS: tuple[str, ...] = get_args(ObjectKind)
SOUNDS: tuple[str, ...] = get_args(SoundKind)
MOODS: tuple[str, ...] = get_args(Mood)

MAX_OBJECTS = 8

# 장소별 기본 소품 (대화에서 물건이 나오지 않아도 공간이 비어 보이지 않게)
PLACE_DEFAULT_OBJECTS: dict[str, list[str]] = {
    "none": [],
    "living_room": ["sofa", "low_table", "crt_tv"],
    "grandma_house": ["low_table", "radio", "clock"],
    "classroom": ["desk", "chair", "chalkboard"],
    "bedroom": ["bed", "lamp", "bookshelf"],
    "playground": ["tree", "swing", "slide"],
    "beach": ["umbrella"],
}


@dataclass
class MemoryScene:
    place: str = "none"
    time_of_day: str = "afternoon"
    objects: list[str] = field(default_factory=list)
    sound: str = "none"
    mood: str = "calm"
    summary: str = ""

    def merge(self, update: dict) -> bool:
        """대화에서 나온 갱신 사항을 반영한다. 장면이 바뀌었으면 True."""
        before = self.snapshot()
        place = update.get("place")
        if place in PLACES and place != "none":
            if place != self.place:
                self.objects = []  # 장소가 바뀌면 소품 초기화
            self.place = place
        if update.get("time_of_day") in TIMES:
            self.time_of_day = update["time_of_day"]
        for obj in update.get("objects") or []:
            if obj in OBJECTS and obj not in self.objects:
                self.objects.append(obj)
        self.objects = self.objects[-MAX_OBJECTS:]
        if update.get("sound") in SOUNDS:
            self.sound = update["sound"]
        if update.get("mood") in MOODS:
            self.mood = update["mood"]
        if update.get("summary"):
            self.summary = str(update["summary"])[:200]
        return self.snapshot() != before

    def all_objects(self) -> list[str]:
        """장소 기본 소품 + 대화에서 나온 물건 (중복 제거, 순서 유지)."""
        result: list[str] = []
        for obj in PLACE_DEFAULT_OBJECTS.get(self.place, []) + self.objects:
            if obj not in result:
                result.append(obj)
        return result[:MAX_OBJECTS]

    def snapshot(self) -> dict:
        return asdict(self)

    def reset(self) -> None:
        self.__init__()
