"""기억 무대 생성기.

MemoryScene → Webots 노드(VRML 문자열). 외부 에셋 없이 기본 도형(Box/Cylinder/Sphere)만으로 소품을 만든다.
build_scene_nodes()는 Webots 없이도 호출 가능하므로 단독 테스트할 수 있다.
"""
from __future__ import annotations

from memory_model import MemoryScene

# ---------- 소품 정의: (도형, 위치 오프셋, 크기, 색) ----------
# 도형: box(size xyz) / cyl(height, radius) / sph(radius)
Part = tuple
OBJECT_PARTS: dict[str, list[Part]] = {
    "crt_tv": [
        ("box", (0, 0, 0.25), (0.45, 0.4, 0.5), (0.35, 0.22, 0.12)),
        ("box", (0, 0.201, 0.3), (0.3, 0.005, 0.26), (0.15, 0.25, 0.2)),   # 화면
        ("cyl", (0.17, 0.201, 0.14), (0.01, 0.025), (0.8, 0.75, 0.6)),     # 다이얼
    ],
    "radio": [
        ("box", (0, 0, 0.12), (0.32, 0.14, 0.2), (0.55, 0.32, 0.15)),
        ("box", (-0.05, 0.071, 0.12), (0.14, 0.003, 0.12), (0.85, 0.8, 0.65)),
        ("cyl", (0.1, 0.071, 0.12), (0.01, 0.025), (0.2, 0.2, 0.2)),
    ],
    "sofa": [
        ("box", (0, 0, 0.2), (1.4, 0.6, 0.4), (0.55, 0.25, 0.2)),
        ("box", (0, -0.25, 0.5), (1.4, 0.12, 0.4), (0.5, 0.22, 0.18)),
    ],
    "low_table": [
        ("cyl", (0, 0, 0.3), (0.04, 0.4), (0.5, 0.33, 0.18)),
        ("cyl", (0, 0, 0.15), (0.3, 0.05), (0.4, 0.26, 0.14)),
    ],
    "chair": [
        ("box", (0, 0, 0.42), (0.4, 0.4, 0.04), (0.6, 0.45, 0.25)),
        ("box", (0, -0.18, 0.65), (0.4, 0.04, 0.4), (0.6, 0.45, 0.25)),
        ("box", (0, 0, 0.2), (0.35, 0.35, 0.4), (0.3, 0.3, 0.32)),
    ],
    "desk": [
        ("box", (0, 0, 0.7), (1.0, 0.5, 0.04), (0.65, 0.5, 0.3)),
        ("box", (0, 0, 0.35), (0.9, 0.4, 0.68), (0.35, 0.35, 0.38)),
    ],
    "chalkboard": [
        ("box", (0, 0, 1.1), (1.8, 0.04, 0.9), (0.12, 0.3, 0.2)),
        ("box", (0, 0.03, 0.62), (1.8, 0.08, 0.04), (0.55, 0.4, 0.25)),
    ],
    "bed": [
        ("box", (0, 0, 0.2), (1.0, 1.9, 0.4), (0.5, 0.35, 0.22)),
        ("box", (0, 0.2, 0.43), (0.95, 1.4, 0.06), (0.85, 0.75, 0.8)),
        ("box", (0, -0.75, 0.45), (0.6, 0.3, 0.1), (0.95, 0.95, 0.92)),
    ],
    "bookshelf": [
        ("box", (0, 0, 0.8), (0.9, 0.3, 1.6), (0.45, 0.3, 0.18)),
        ("box", (0, 0.13, 1.0), (0.8, 0.05, 0.25), (0.7, 0.2, 0.2)),
        ("box", (0, 0.13, 0.55), (0.8, 0.05, 0.25), (0.2, 0.35, 0.6)),
    ],
    "lamp": [
        ("cyl", (0, 0, 0.6), (1.2, 0.015), (0.3, 0.3, 0.3)),
        ("cyl", (0, 0, 1.25), (0.25, 0.18), (0.95, 0.85, 0.55)),
    ],
    "photo_frame": [
        ("box", (0, 0, 0.15), (0.22, 0.03, 0.3), (0.6, 0.45, 0.2)),
        ("box", (0, 0.016, 0.15), (0.17, 0.003, 0.24), (0.85, 0.8, 0.7)),
    ],
    "tree": [
        ("cyl", (0, 0, 0.7), (1.4, 0.1), (0.4, 0.27, 0.15)),
        ("sph", (0, 0, 1.7), (0.7,), (0.25, 0.5, 0.2)),
    ],
    "swing": [
        ("box", (0, -0.6, 0.9), (0.06, 0.06, 1.8), (0.7, 0.2, 0.15)),
        ("box", (0, 0.6, 0.9), (0.06, 0.06, 1.8), (0.7, 0.2, 0.15)),
        ("box", (0, 0, 1.8), (0.08, 1.3, 0.08), (0.7, 0.2, 0.15)),
        ("box", (0, 0, 0.45), (0.3, 0.45, 0.04), (0.85, 0.7, 0.2)),
    ],
    "slide": [
        ("box", (-0.5, 0, 0.6), (0.4, 0.5, 1.2), (0.2, 0.45, 0.7)),
        ("box", (0.25, 0, 0.6), (1.3, 0.45, 0.04), (0.9, 0.75, 0.2)),
    ],
    "umbrella": [
        ("cyl", (0, 0, 0.9), (1.8, 0.02), (0.9, 0.9, 0.9)),
        ("cyl", (0, 0, 1.8), (0.05, 0.8), (0.9, 0.3, 0.25)),
    ],
    "clock": [
        ("box", (0, 0, 1.3), (0.3, 0.06, 0.4), (0.45, 0.28, 0.14)),
        ("cyl", (0, 0.035, 1.35), (0.01, 0.1), (0.95, 0.92, 0.8)),
    ],
}

# 소품을 놓을 자리 (무대 로컬 좌표, 관찰자는 +Y 쪽). 앞에서부터 순서대로 채움
SLOTS = [(0, -0.4), (-0.9, -0.5), (0.9, -0.5), (0.4, 0.3), (-0.5, 0.3), (1.2, 0.4), (-1.2, 0.4), (0, 0.8)]
# 벽에 붙어야 하는 소품
WALL_OBJECTS = {"chalkboard", "clock", "bookshelf"}
# 다른 소품 위에 올라가는 소품 (받침대 높이)
TABLETOP = {"radio": 0.33, "photo_frame": 0.33}

PLACE_STYLE = {
    # 바닥색, 벽색 (벽 없음 = None)
    "none": ((0.2, 0.2, 0.22), None),
    "living_room": ((0.55, 0.4, 0.25), (0.85, 0.78, 0.6)),
    "grandma_house": ((0.75, 0.6, 0.35), (0.9, 0.85, 0.7)),
    "classroom": ((0.5, 0.42, 0.32), (0.75, 0.85, 0.75)),
    "bedroom": ((0.6, 0.48, 0.38), (0.8, 0.75, 0.85)),
    "playground": ((0.82, 0.72, 0.5), None),
    "beach": ((0.93, 0.85, 0.6), (0.35, 0.6, 0.85)),  # 벽 = 바다 배경
}

TIME_LIGHT = {
    "morning": ((1.0, 0.95, 0.85), 1.4),
    "afternoon": ((1.0, 1.0, 0.95), 1.8),
    "evening": ((1.0, 0.7, 0.45), 1.1),
    "night": ((0.45, 0.5, 0.85), 0.6),
}
MOOD_INTENSITY = {"warm": 1.1, "nostalgic": 0.9, "calm": 1.0, "lonely": 0.7, "tense": 0.8, "joyful": 1.2}


def _fmt(values) -> str:
    return " ".join(f"{v:.3f}" for v in values)


def _shape(kind: str, size, color) -> str:
    if kind == "box":
        geometry = f"Box {{ size {_fmt(size)} }}"
    elif kind == "cyl":
        geometry = f"Cylinder {{ height {size[0]:.3f} radius {size[1]:.3f} }}"
    else:
        geometry = f"Sphere {{ radius {size[0]:.3f} }}"
    return (f"Shape {{ appearance PBRAppearance {{ baseColor {_fmt(color)} roughness 0.8 metalness 0 }} "
            f"geometry {geometry} }}")


def _solid(name: str, position, parts: list[Part]) -> str:
    children = " ".join(
        f"Pose {{ translation {_fmt(offset)} children [ {_shape(kind, size, color)} ] }}"
        for kind, offset, size, color in parts
    )
    return f'Solid {{ translation {_fmt(position)} name "{name}" children [ {children} ] }}'


def build_scene_nodes(scene: MemoryScene) -> list[str]:
    """장면 → VRML 노드 문자열 목록 (무대 Pose의 children에 넣을 것)."""
    floor_color, wall_color = PLACE_STYLE.get(scene.place, PLACE_STYLE["none"])
    nodes = [_solid("mem_floor", (0, 0, 0.006), [("box", (0, 0, 0), (3.0, 2.4, 0.006), floor_color)])]
    if wall_color is not None:
        nodes.append(_solid("mem_wall", (0, -1.2, 0), [("box", (0, 0, 1.0), (3.0, 0.05, 2.0), wall_color)]))

    # 받침대(밥상/책상)를 먼저 배치해야 그 위에 소품을 올릴 수 있음
    objects = sorted(scene.all_objects(), key=lambda o: o not in ("low_table", "desk"))
    slot_iter = iter(SLOTS)
    table_pos = None
    on_table = 0
    for obj in objects:
        if obj in WALL_OBJECTS:
            x = {"chalkboard": 0.0, "clock": 1.0, "bookshelf": -1.0}[obj]
            pos = (x, -1.05, 0.0)
        elif obj in TABLETOP and table_pos is not None:
            height = TABLETOP[obj] if "low_table" in objects else 0.72  # 책상 위면 더 높게
            pos = (table_pos[0] - 0.12 + 0.24 * on_table, table_pos[1], height)
            on_table += 1
        else:
            sx, sy = next(slot_iter, (0.0, 0.0))
            pos = (sx, sy, 0.0)
            if obj in ("low_table", "desk"):
                table_pos = pos
        nodes.append(_solid(f"mem_{obj}", pos, OBJECT_PARTS[obj]))
    return nodes


def light_settings(scene: MemoryScene, soft: bool = False) -> tuple[tuple[float, float, float], float]:
    color, intensity = TIME_LIGHT.get(scene.time_of_day, TIME_LIGHT["afternoon"])
    intensity *= MOOD_INTENSITY.get(scene.mood, 1.0)
    if soft:  # 고통 지수가 오르면 자극을 낮춤
        intensity *= 0.6
    return color, intensity


class SceneBuilder:
    """Webots Supervisor로 MEMORY_STAGE에 장면을 생성/삭제한다."""

    def __init__(self, supervisor):
        stage = supervisor.getFromDef("MEMORY_STAGE")
        light = supervisor.getFromDef("MEMORY_LIGHT")
        if stage is None or light is None:
            raise RuntimeError("월드에 DEF MEMORY_STAGE / DEF MEMORY_LIGHT 가 필요합니다.")
        self.children = stage.getField("children")
        self.light_color = light.getField("color")
        self.light_intensity = light.getField("intensity")
        self.active = False

    def clear(self) -> None:
        while self.children.getCount() > 0:
            self.children.removeMF(0)
        self.light_intensity.setSFFloat(0.0)
        self.active = False

    def show(self, scene: MemoryScene, soft: bool = False) -> None:
        self.clear()
        for node in build_scene_nodes(scene):
            self.children.importMFNodeFromString(-1, node)
        self.set_light(scene, soft)
        self.active = True

    def set_light(self, scene: MemoryScene, soft: bool = False) -> None:
        color, intensity = light_settings(scene, soft)
        self.light_color.setSFColor(list(color))
        self.light_intensity.setSFFloat(intensity)
