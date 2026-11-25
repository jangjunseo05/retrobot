"""내담자 역할 채팅 클라이언트. Webots에서 시뮬레이션을 실행한 뒤:

    python tools/chat_client.py

'/stop' = 즉시 재현 중단, '/quit' = 종료
"""
import json
import os
import socket
import sys
import threading

HOST, PORT = "127.0.0.1", int(os.environ.get("RETROBOT_PORT", "5577"))


def receive(sock):
    buf = b""
    while chunk := sock.recv(4096):
        buf += chunk
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            msg = json.loads(line.decode("utf-8"))
            if msg["type"] == "reply":
                meta = f"[{msg['phase']} · {msg['emotion']} · 고통 {msg['distress']} · {msg['safety']}]"
                print(f"\n🤖 retrobot {meta}\n   {msg['text']}")
                if msg.get("scene"):
                    s = msg["scene"]
                    print(f"   📺 기억 무대: {s['place']} / {s['time_of_day']} / 소리 {s['sound']} / 물건 {s['objects']}")
            else:
                print(f"\n· {msg['text']}")
            print("나> ", end="", flush=True)
    print("\n연결이 끊겼습니다.")
    os._exit(0)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        sock = socket.create_connection((HOST, PORT))
    except OSError:
        print(f"{HOST}:{PORT}에 연결할 수 없습니다. Webots에서 retrobot.wbt를 먼저 실행하세요.")
        return
    threading.Thread(target=receive, args=(sock,), daemon=True).start()
    while True:
        text = input("나> ").strip()
        if text == "/quit":
            break
        if text:
            sock.sendall((text + "\n").encode("utf-8"))
    sock.close()


if __name__ == "__main__":
    main()
