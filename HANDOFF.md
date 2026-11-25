# retrobot 인계 문서

> 작성일: 2026-11-25 · 다른 노트북에서 작업을 이어가기 위한 문서

## 1. 프로젝트 요약

- **컨셉**: 레트로 외형(CRT 얼굴, 다이얼, 안테나)의 로봇이 내담자와 대화하며 과거 기억을 끌어내고,
  기억 속 장소·물건·소리·분위기를 시뮬레이션 무대에 재현해 회상 기반 심리 치료를 돕는다.
- **목적**: 실제 로봇을 제작하기 전에 시뮬레이션으로 검증
- **플랫폼**: Webots R2025a 이상 + Python 컨트롤러
  - 선택 이유: 무료이고 Windows에서 바로 실행되며 GPU 부담이 적다. 로봇 장치(모터, 디스플레이, LED, 스피커)가 내장되어 있고, 나중에 ROS 2로 옮기기 쉽다.
  - 제외한 후보: Isaac Sim(RTX GPU 필요, 이전 노트북 GTX 1650 Ti), Gazebo(Windows 지원이 불편함), Unity(하드웨어 검증 근거로 약함)
- **대화 AI**: Claude API(`claude-opus-5-5`), 구조화 출력(JSON)으로 대사·표정·몸짓·기억·고통 지수를 한 번에 받는다.
  API 키가 없으면 키워드 기반 Mock 엔진으로 동작한다.

## 2. 현재 진행 상태 (1단계 뼈대 완료)

| 항목 | 상태 |
|---|---|
| 로봇 모델 `protos/RetroBot.proto` | ✅ 작성 완료 · ⚠️ Webots 실행 확인 전 |
| 월드 `worlds/retrobot.wbt` (치료실 + 기억 무대) | ✅ 작성 완료 · ⚠️ Webots 실행 확인 전 |
| 컨트롤러 (대화/기억/장면/표정/소리/안전/로그) | ✅ 작성 완료 |
| 효과음 9종 `assets/sounds/` | ✅ 생성 완료 (`tools/gen_sounds.py`) |
| 단위 테스트 9개 (Webots 없이 실행) | ✅ 전부 통과 |
| Claude API 요청 형식 | ✅ 확인 (잘못된 키로 보냈을 때 인증 오류 401만 발생 = 요청 구조는 정상) |
| 실제 API 키로 대화 | ❌ 아직 안 해봄 |
| **Webots에서 실제 실행** | ❌ **아직 안 해봄** (이전 노트북에 Webots 미설치) |

## 3. 새 노트북 세팅

```bash
git clone https://github.com/jangjunseo05/retrobot.git
cd retrobot
python -m venv .venv            # 권장: 전용 가상환경
# Windows: .venv\Scripts\activate   /   macOS·Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover tests -v   # 9개 통과 확인
```

1. **Webots R2025a 이상** 설치: https://cyberbotics.com
2. Webots가 위 가상환경의 Python을 쓰게 설정: *Tools > Preferences > Python command*에
   `.venv` 안의 python 실행 파일 경로를 입력한다 (Windows 예: `C:\...\retrobot\.venv\Scripts\python.exe`)
3. (선택) Claude 사용: 환경 변수 `ANTHROPIC_API_KEY` 설정. 설정하지 않으면 Mock 엔진으로 동작한다.
   - 강제 선택: `RETROBOT_ENGINE=mock` 또는 `RETROBOT_ENGINE=claude`
   - Webots를 실행하기 **전에** 환경 변수를 설정해야 컨트롤러가 읽을 수 있다.
4. Webots에서 `worlds/retrobot.wbt` 열기 → ▶ 재생
5. 다른 터미널에서 `python tools/chat_client.py` → 내담자 역할로 대화 (`/stop` 중단, `/quit` 종료)

효과음 파일은 레포에 포함되어 있다. 지워졌다면 `python tools/gen_sounds.py`로 다시 만든다.

## 4. 구조

```
protos/RetroBot.proto          로봇: CRT 얼굴 Display "face"(128x96), 모터 neck_pan / neck_tilt /
                               left_shoulder / right_shoulder, LED "antenna_led"(RGB), Speaker "speaker"
                               정면 방향 = +X
worlds/retrobot.wbt            로봇(원점) ↔ 내담자 의자(x=1.3). 기억 무대 DEF MEMORY_STAGE(0.6, -3.2),
                               무대 조명 DEF MEMORY_LIGHT
controllers/retrobot/
  retrobot.py     Supervisor 진입점. TCP 127.0.0.1:5577 채팅 서버, 대화는 별도 스레드에서 처리
  session.py      한 턴 처리: 발화 → 대화 → 기억 merge → 안전 판단 → TurnOutcome → logs/*.jsonl
  dialogue.py     ClaudeDialogue(구조화 출력 TurnResult) / MockDialogue / create_dialogue()
  memory_model.py MemoryScene + 허용값 목록(장소 7, 물건 16, 소리 9, 분위기 6)
  scene_builder.py 장면 → VRML 문자열(기본 도형만 사용) → importMFNodeFromString, 시간대/분위기별 조명
  expression.py   CRT 표정 6종, 몸짓 키프레임 6종(idle/nod/tilt/wave/comfort/point_stage), LED 색
  audio.py        배경음 반복 재생/정지, 응답 시 비프음
  safety.py       고통 지수 기준: 5 이상 soft, 7 이상 stop, 연속 2턴 동안 3 이하일 때 해제. /stop·"그만" 즉시 중단
tools/            chat_client.py, gen_sounds.py
tests/test_core.py  Webots controller 모듈을 가짜로 대체해 핵심 로직을 테스트
```

**세션 단계**: rapport → recall(기억 탐색, 재현 전 동의 확인) → reenact(무대 재현) → closure(무대 정리)
/ grounding(고통이 크거나 중단 신호가 오면 무대를 지우고 호흡·감각 안내)

**설계 원칙**
- 안전 규칙은 LLM 판단과 별개로 로봇 쪽(`safety.py`, `session.py`)에서 강제한다. LLM이 reenact=true를 보내도 stop 상태면 재현하지 않는다.
- `session / dialogue / memory_model / safety`는 Webots에 의존하지 않는다 → 실제 로봇에서 그대로 재사용
- 대화 기록에서 Claude 응답 블록(thinking 포함)은 수정하지 않고 그대로 다시 보낸다 (`_echo_blocks`).

## 5. 다음 할 일 (우선순위 순)

1. **Webots 첫 실행 확인**: 아래 항목을 확인하고, 문제가 있으면 수정한다.
   - [ ] 월드 로딩 시 PROTO/문법 오류 없음 (Webots 콘솔 확인)
   - [ ] CRT 얼굴이 정면(+X)에 똑바로 보이는지 (뒤집힘·좌우 반전 여부) → `RetroBot.proto`의 Display `rotation`
   - [ ] 안테나 LED 색이 감정에 따라 바뀌는지 (`color [ ]` + `gradual TRUE` RGB 모드)
   - [ ] 몸짓(wave, point_stage)의 팔 방향이 자연스러운지 → `expression.py`의 GESTURES 각도 부호
   - [ ] 기억 무대에 소품이 겹치지 않게 배치되는지 → `scene_builder.py`의 SLOTS
   - [ ] 배경음 재생/정지 확인 (`Speaker.stop(path)`)
2. Mock 엔진으로 시나리오 한 바퀴 돌려보기 (예: "어릴 때 비 오는 날 외할머니 집에서 라디오를 들었어" → "네 보여줘" → "/stop")
3. API 키를 설정하고 Claude로 실제 대화 테스트. 응답 속도가 느리면 `dialogue.py`의 effort는 이미 `low`이니 프롬프트 길이를 점검한다.
4. 이후 확장 후보: 음성 입출력(STT/TTS, Webots 내장 TTS는 한국어 미지원), 기억 장소·소품 추가,
   세션 로그로 검증 지표 만들기(고통 지수 추이, 재현 횟수, 중단 횟수), ROS 2 연동

## 6. 참고·주의

- 실제 내담자를 대상으로 하려면 IRB 승인, 대화 로그 개인정보 처리, 임상 전문가 감독이 필요하다. 현재는 가상 시나리오로만 검증한다.
- `logs/`(세션 대화 로그)는 `.gitignore`에 포함되어 있으며 레포에 올라가지 않는다. **이 레포는 public이므로** API 키·대화 로그를 커밋하지 말 것.
- 이전 노트북에서 anthropic SDK를 conda 기본 환경에 설치하면서 protobuf가 7.x로 올라가 streamlit과 충돌했다.
  새 노트북에서는 위의 `.venv` 전용 가상환경을 쓰면 이 문제가 생기지 않는다.
- 테스트 환경: Python 3.12, anthropic 2.14.0, pydantic 2.8
