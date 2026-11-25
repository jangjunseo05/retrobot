"""Webots 없이 핵심 로직을 검증한다.

    python -m unittest discover tests -v
"""
import os
import sys
import tempfile
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "controllers", "retrobot"))

# ---- Webots `controller` 모듈 대역 ----
fake_controller = types.ModuleType("controller")


class _Recorder:
    def __init__(self, name):
        self.name, self.calls = name, []

    def __getattr__(self, attr):
        def call(*args):
            self.calls.append((attr, args))
        return call

    def getWidth(self):
        return 128

    def getHeight(self):
        return 96


class _Speaker:
    played = []

    @staticmethod
    def playSound(left, right, path, volume, pitch, balance, loop):
        _Speaker.played.append((os.path.basename(path), loop))


fake_controller.Speaker = _Speaker
fake_controller.Supervisor = object
sys.modules["controller"] = fake_controller

from dialogue import MockDialogue, TurnResult  # noqa: E402
from expression import Expression  # noqa: E402
from memory_model import MemoryScene  # noqa: E402
from safety import SafetyMonitor  # noqa: E402
from scene_builder import SceneBuilder, build_scene_nodes  # noqa: E402
from session import TherapySession  # noqa: E402


class FakeField:
    def __init__(self):
        self.items, self.value = [], None

    def getCount(self):
        return len(self.items)

    def removeMF(self, i):
        self.items.pop(i)

    def importMFNodeFromString(self, pos, s):
        self.items.append(s)

    def setSFColor(self, v):
        self.value = v

    def setSFFloat(self, v):
        self.value = v


class FakeNode:
    def __init__(self):
        self.fields = {}

    def getField(self, name):
        return self.fields.setdefault(name, FakeField())


class FakeRobot:
    def __init__(self):
        self.devices, self.nodes = {}, {"MEMORY_STAGE": FakeNode(), "MEMORY_LIGHT": FakeNode()}

    def getDevice(self, name):
        return self.devices.setdefault(name, _Recorder(name))

    def getFromDef(self, name):
        return self.nodes.get(name)


class SceneTests(unittest.TestCase):
    def test_merge_and_defaults(self):
        s = MemoryScene()
        self.assertTrue(s.merge({"place": "grandma_house", "objects": ["radio", "not_a_thing"], "sound": "rain"}))
        self.assertEqual(s.objects, ["radio"])
        self.assertEqual(s.all_objects(), ["low_table", "radio", "clock"])
        self.assertFalse(s.merge({"place": "none", "objects": []}))  # 변화 없음
        s.merge({"place": "classroom"})
        self.assertEqual(s.objects, [])  # 장소가 바뀌면 소품 초기화

    def test_vrml_well_formed_for_every_place(self):
        from memory_model import OBJECTS, PLACES
        for place in PLACES:
            s = MemoryScene(place=place, objects=list(OBJECTS))
            for node in build_scene_nodes(s):
                self.assertEqual(node.count("{"), node.count("}"), node)
                self.assertEqual(node.count("["), node.count("]"), node)
                self.assertTrue(node.startswith("Solid {"))

    def test_tabletop_items_sit_on_table(self):
        nodes = build_scene_nodes(MemoryScene(place="grandma_house", objects=["radio", "photo_frame"]))
        radio = next(n for n in nodes if '"mem_radio"' in n)
        self.assertEqual(radio.split()[5], "0.330")  # "Solid { translation x y z" → z = 밥상 높이

    def test_scene_builder_with_fake_supervisor(self):
        robot = FakeRobot()
        sb = SceneBuilder(robot)
        sb.show(MemoryScene(place="living_room", time_of_day="evening"))
        children = robot.nodes["MEMORY_STAGE"].getField("children")
        self.assertGreater(children.getCount(), 3)
        self.assertGreater(robot.nodes["MEMORY_LIGHT"].getField("intensity").value, 0)
        sb.clear()
        self.assertEqual(children.getCount(), 0)
        self.assertEqual(robot.nodes["MEMORY_LIGHT"].getField("intensity").value, 0.0)


class SafetyTests(unittest.TestCase):
    def test_levels_and_recovery(self):
        m = SafetyMonitor()
        self.assertEqual(m.update(2), "normal")
        self.assertEqual(m.update(5), "soft")
        self.assertEqual(m.update(8), "stop")
        self.assertEqual(m.update(2), "stop")   # 한 번 안정으로는 해제 안 됨
        self.assertEqual(m.update(1), "normal")

    def test_stop_words(self):
        m = SafetyMonitor()
        self.assertTrue(m.is_stop_request("/stop"))
        self.assertTrue(m.is_stop_request("그만할래"))
        self.assertFalse(m.is_stop_request("그때 할머니가 그만 웃으셨어"))


class SessionTests(unittest.TestCase):
    def test_mock_session_flow(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = TherapySession(MockDialogue(), log_dir=tmp)
            o1 = s.handle("안녕")
            self.assertEqual(o1.phase, "rapport")
            o2 = s.handle("어릴 때 비 오는 날 외할머니 집에서 라디오를 들었어")
            self.assertFalse(o2.show_scene)  # 동의 전에는 재현하지 않음
            self.assertEqual(s.scene.place, "grandma_house")
            o3 = s.handle("네 보여줘")
            self.assertTrue(o3.show_scene)
            self.assertIn(o3.sound, ("rain", "radio_static"))  # Mock은 먼저 매칭된 소리 하나만 고름
            o4 = s.handle("갑자기 무서워서 숨이 막혀, 못 하겠어")
            self.assertEqual(o4.safety, "stop")
            self.assertTrue(o4.clear_scene)
            self.assertEqual(o4.sound, "none")
            o5 = s.handle("/stop")
            self.assertEqual(o5.phase, "grounding")
            with open(s.log_path, encoding="utf-8") as f:
                self.assertEqual(len(f.readlines()), 5)

    def test_reenact_blocked_while_stopped(self):
        class Scripted:
            name = "scripted"

            def respond(self, text, note):
                return TurnResult.model_validate({
                    "reply": "…", "emotion": "calm", "gesture": "idle", "phase": "reenact", "distress": 8,
                    "reenact": True, "memory": {"place": "beach", "time_of_day": None, "objects": [],
                                                "sound": "waves", "mood": None, "summary": ""}})

        o = TherapySession(Scripted()).handle("바다")
        self.assertFalse(o.show_scene)  # LLM이 재현하라고 해도 고통이 높으면 로봇이 막음
        self.assertEqual(o.safety, "stop")


class ExpressionTests(unittest.TestCase):
    def test_every_emotion_and_gesture_runs(self):
        from expression import GESTURES, LED_COLORS
        robot = FakeRobot()
        e = Expression(robot)
        t = 0.0
        for emotion in LED_COLORS:
            for gesture in GESTURES:
                e.set_emotion(emotion)
                e.play_gesture(gesture, t)
                e.talk("안녕하세요", t)
                for _ in range(10):
                    t += 0.5
                    e.update(t)
        self.assertTrue(robot.devices["face"].calls)
        self.assertTrue(any(c[0] == "setPosition" for c in robot.devices["right_shoulder"].calls))


if __name__ == "__main__":
    unittest.main()
