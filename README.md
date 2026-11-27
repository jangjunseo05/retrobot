# retrobot

레트로 외형의 로봇이 내담자와 대화하며 과거 기억을 끌어내고, 그 기억 속 **장소 · 물건 · 소리 · 분위기**를
시뮬레이션 무대에 재현해 회상 기반 심리 치료를 돕는 프로젝트. 실제 로봇 제작 전 검증을 위해 **Webots**에서 구현한다.

## 구성

```
protos/RetroBot.proto        로봇 모델: CRT 얼굴(Display), 고개 pan/tilt, 양팔, 안테나 LED, 스피커
worlds/retrobot.wbt          치료실(로봇 + 내담자) + 기억 무대(MEMORY_STAGE, MEMORY_LIGHT)
controllers/retrobot/
  retrobot.py                Supervisor 컨트롤러 (TCP 채팅 서버, 시뮬레이션 루프)
  session.py                 세션 진행: 발화 → 대화 → 기억 갱신 → 안전 판단 → 행동 결정 → 로그
  dialogue.py                Claude 대화 엔진(구조화 출력) / Mock 엔진
  memory_model.py            기억 장면 데이터 (장소·시간대·물건·소리·분위기)
  scene_builder.py           장면 → Webots 노드 생성, 조명
  expression.py              CRT 표정, 몸짓 키프레임, LED
  audio.py                   배경음 재생
  safety.py                  고통 지수 기반 자극 조절, 중단 신호
tools/chat_client.py         내담자 역할 채팅 클라이언트
tools/gen_sounds.py          효과음 생성 (assets/sounds/*.wav)
tests/                       Webots 없이 돌리는 단위 테스트(test_core) + 통합 테스트(test_e2e)
logs/                        세션 로그 (JSONL, 검증 지표용)
```

## 실행

1. [Webots R2025a 이상](https://cyberbotics.com) 설치
2. 의존성: `pip install -r requirements.txt`
3. 효과음 생성: `python tools/gen_sounds.py` (이미 생성되어 있음)
4. Claude 사용 시 `ANTHROPIC_API_KEY` 환경 변수 설정 (없으면 키워드 기반 Mock 엔진으로 동작)
   - 강제 선택: `RETROBOT_ENGINE=mock` 또는 `RETROBOT_ENGINE=claude`
5. Webots에서 `worlds/retrobot.wbt` 열기 → 재생
6. 터미널에서 `python tools/chat_client.py` → 내담자로서 대화

Webots가 다른 Python을 쓰면 *Tools > Preferences > Python command*에 anthropic이 설치된 Python 경로를 지정한다.

## 세션 흐름

| 단계 | 로봇 행동 |
|---|---|
| rapport | 인사, 손 흔들기 |
| recall | 개방형 질문으로 기억 탐색, 장소/물건/소리 추출 → **재현 전 동의 확인** |
| reenact | 무대를 가리키며 기억 공간 생성, 시간대·분위기에 맞춘 조명, 배경음 |
| closure | 의미 정리, 무대 정리 후 현재로 복귀 |
| grounding | (고통 ≥ 7 또는 `/stop`) 재현 즉시 중단, 호흡·감각 안내, 위로 몸짓 |

안전 규칙은 LLM 판단과 별개로 로봇 쪽(`safety.py`)에서 강제한다: 고통 5 이상이면 조명·소리를 약하게,
7 이상이면 무대를 지우고 그라운딩. 연속 2턴 안정(≤3)되어야 해제된다.

## 테스트

```
python -m unittest discover tests -v
```

## 실제 로봇으로 옮길 때

- `session.py`, `dialogue.py`, `memory_model.py`, `safety.py`는 Webots 비의존 → 그대로 재사용
- `expression.py`/`audio.py`의 장치 호출만 실제 하드웨어(서보, LCD, 스피커)나 ROS 2 토픽으로 교체
- 기억 무대(`scene_builder.py`)는 프로젝터·디스플레이·AR 장치 출력으로 대체
- 실제 내담자 대상 실험 전에는 IRB 승인, 개인정보(대화 로그) 처리 방침, 임상 전문가 감독이 필요하다
