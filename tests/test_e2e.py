"""컨트롤러 전체(retrobot.main)를 가짜 Webots 위에서 실행하는 통합 테스트.

채팅 서버 접속 → 대화(Mock 엔진) → 기억 무대 생성 → 배경음 → /stop 중단 까지 한 번에 검증한다.
"""
import json
import os
import socket
import sys
import tempfile
import threading
import time
import unittest

import test_core as tc  # 가짜 controller 모듈과 FakeRobot을 설치함

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class EndToEndTest(unittest.TestCase):
    def test_full_session(self):
        port = _free_port()
        os.environ["RETROBOT_ENGINE"] = "mock"
        os.environ["RETROBOT_PORT"] = str(port)
        done = threading.Event()
        holder = {}

        class FakeSupervisor(tc.FakeRobot):
            def __init__(self):
                super().__init__()
                self.t = 0.0
                holder["robot"] = self

            def getBasicTimeStep(self):
                return 32

            def getTime(self):
                return self.t

            def step(self, ms):
                self.t += ms / 1000
                time.sleep(0.002)
                return -1 if done.is_set() or self.t > 120 else 0

        tc.fake_controller.Supervisor = FakeSupervisor
        sys.path.insert(0, os.path.join(ROOT, "controllers", "retrobot"))
        sys.modules.pop("retrobot", None)
        import retrobot  # noqa: E402  (RETROBOT_PORT를 읽도록 매번 새로 import)

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        retrobot.LOG_DIR = tmp.name
        replies, stage_counts, errors = [], [], []

        def client():
            try:
                for _ in range(100):  # 서버가 뜰 때까지 대기
                    try:
                        sock = socket.create_connection(("127.0.0.1", port))
                        break
                    except OSError:
                        time.sleep(0.05)
                stream = sock.makefile("rb")
                self.assertEqual(json.loads(stream.readline())["type"], "hello")
                for line in ("안녕", "어릴 때 비가 오는 날 외할머니 집에서 라디오를 들었어", "네 보여줘",
                             "겨울에 서울 갔던 날도 생각나", "/stop"):
                    sock.sendall((line + "\n").encode("utf-8"))
                    replies.append(json.loads(stream.readline()))
                    time.sleep(0.1)  # 메인 루프가 무대를 갱신할 시간
                    stage_counts.append(holder["robot"].nodes["MEMORY_STAGE"].getField("children").getCount())
                sock.close()
            except Exception as exc:  # 실패는 메인 스레드에서 보고
                errors.append(exc)
            finally:
                done.set()

        tc._Speaker.played.clear()
        threading.Thread(target=client, daemon=True).start()
        retrobot.main()

        self.assertFalse(errors, errors)
        self.assertEqual([r["phase"] for r in replies], ["rapport", "recall", "reenact", "recall", "grounding"])
        self.assertIsNone(replies[1]["scene"])                     # 동의 전에는 무대 없음
        self.assertEqual(replies[2]["scene"]["place"], "grandma_house")
        self.assertGreater(stage_counts[2], 0)                     # 동의 후 무대 생성
        self.assertEqual(replies[3]["distress"], 0)                # '서울/겨울'이 고통으로 잡히지 않음
        self.assertEqual(replies[4]["safety"], "stop")
        self.assertEqual(stage_counts[4], 0)                       # /stop → 무대 비움
        speaker = holder["robot"].devices["speaker"]
        self.assertTrue(any(c[0] == "stop" for c in speaker.calls))  # 배경음 정지
        self.assertTrue(any(loop for _, loop in tc._Speaker.played))  # 배경음(루프) 재생됨
        logs = os.listdir(tmp.name)
        self.assertEqual(len(logs), 1)
        with open(os.path.join(tmp.name, logs[0]), encoding="utf-8") as f:
            self.assertEqual(len(f.readlines()), 5)


if __name__ == "__main__":
    unittest.main()
