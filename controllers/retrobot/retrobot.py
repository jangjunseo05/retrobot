"""retrobot Webots 컨트롤러 (Supervisor).

내담자 입력은 TCP(127.0.0.1:5577)로 받는다 → tools/chat_client.py 로 접속.
대화 엔진 호출은 시간이 걸리므로 별도 스레드에서 처리하고, 시뮬레이션 루프는 표정/모터/무대만 갱신한다.
"""
from __future__ import annotations

import json
import os
import queue
import socket
import sys
import threading

from controller import Supervisor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from audio import Audio  # noqa: E402
from dialogue import create_dialogue  # noqa: E402
from expression import Expression  # noqa: E402
from scene_builder import SceneBuilder  # noqa: E402
from session import TherapySession  # noqa: E402

HOST, PORT = "127.0.0.1", int(os.environ.get("RETROBOT_PORT", "5577"))
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "logs")


class ChatServer(threading.Thread):
    """한 번에 한 명의 채팅 클라이언트. 한 줄 = 한 발화(UTF-8)."""

    def __init__(self, inbox: queue.Queue):
        super().__init__(daemon=True)
        self.inbox = inbox
        self.conn: socket.socket | None = None
        self.lock = threading.Lock()

    def run(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, PORT))
        srv.listen(1)
        print(f"[retrobot] 채팅 대기 중: {HOST}:{PORT}  →  python tools/chat_client.py")
        while True:
            conn, _ = srv.accept()
            with self.lock:
                self.conn = conn
            self.send({"type": "hello", "text": "retrobot에 연결되었습니다. '/stop'으로 언제든 멈출 수 있어요."})
            buf = b""
            try:
                while chunk := conn.recv(4096):
                    buf += chunk
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        text = line.decode("utf-8", errors="replace").strip()
                        if text:
                            self.inbox.put(text)
            except OSError:
                pass
            with self.lock:
                self.conn = None
            print("[retrobot] 클라이언트 연결 종료")

    def send(self, payload: dict):
        with self.lock:
            if self.conn:
                try:
                    self.conn.sendall((json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))
                except OSError:
                    self.conn = None


def main():
    robot = Supervisor()
    step = int(robot.getBasicTimeStep())

    expression = Expression(robot)
    audio = Audio(robot)
    stage = SceneBuilder(robot)
    stage.clear()
    session = TherapySession(create_dialogue(), log_dir=LOG_DIR)
    print(f"[retrobot] 대화 엔진: {session.dialogue.name}")

    inbox: queue.Queue[str] = queue.Queue()
    outbox: queue.Queue = queue.Queue()
    server = ChatServer(inbox)
    server.start()

    busy = threading.Event()

    def worker():
        while True:
            text = inbox.get()
            busy.set()
            try:
                outbox.put(session.handle(text))
            except Exception as exc:  # API 오류 등 — 세션은 계속
                outbox.put(exc)
            finally:
                busy.clear()

    threading.Thread(target=worker, daemon=True).start()
    expression.set_emotion("neutral")

    while robot.step(step) != -1:
        now = robot.getTime()
        try:
            outcome = outbox.get_nowait()
        except queue.Empty:
            outcome = None

        if isinstance(outcome, Exception):
            print(f"[retrobot] 대화 오류: {outcome}")
            server.send({"type": "error", "text": f"(연결 문제가 있었어요: {outcome})"})
            expression.set_emotion("concerned")
        elif outcome is not None:
            expression.set_emotion(outcome.emotion)
            expression.play_gesture(outcome.gesture, now)
            expression.talk(outcome.reply, now)
            audio.beep()
            if outcome.clear_scene:
                stage.clear()
            elif outcome.show_scene:
                stage.show(session.scene, soft=outcome.soft)
            elif stage.active:
                stage.set_light(session.scene, soft=outcome.soft)
            audio.play_ambient(outcome.sound, volume=0.3 if outcome.soft else 0.6)
            server.send({"type": "reply", "text": outcome.reply, "phase": outcome.phase,
                         "emotion": outcome.emotion, "distress": outcome.distress, "safety": outcome.safety,
                         "scene": outcome.scene if stage.active else None})
            print(f"[retrobot] ({outcome.phase}/{outcome.emotion}/고통 {outcome.distress}/{outcome.safety}) {outcome.reply}")

        if busy.is_set() and int(now * 2) % 2 == 0:
            expression.led.set(0x202020)  # 생각 중: 안테나 깜빡임
        elif busy.is_set():
            expression.led.set(0xC080FF)
        expression.update(now)


if __name__ == "__main__":
    main()
