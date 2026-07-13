# 아키텍처

## 프로젝트 구조

```
auto_gemma/
├─ main.py        # 진입점 (QApplication 부트스트랩, 테마, 마법사 창)
├─ app/           # config(경로·모델 카탈로그·상수), theme(라이트 QSS/팔레트)
├─ core/          # 순수 로직 (Qt 비의존 — 테스트 가능)
│  ├─ ollama_client.py   # httpx: probe/tags/pull(stream)/chat(stream,멀티모달)/embed/delete
│  ├─ installer.py       # winget/OllamaSetup(Win), Homebrew(mac) 무음 설치
│  ├─ system_info.py     # OS/RAM/VRAM/GPU 감지 (플랫폼별)
│  ├─ recommend.py       # VRAM·RAM → 모델 매핑 + 제한 요인
│  ├─ rag/               # loaders(txt/md/pdf/docx), chunker, store(sqlite+numpy)
│  └─ persistence/       # conversations, bots (JSON)
├─ workers/       # QRunnable 워커 (core ↔ Qt 신호 브리지, 취소 가능)
└─ ui/            # PySide6 UI
   ├─ wizard/     # 설치 마법사 창 (spec_card, ollama_section, model_manager)
   ├─ chat/       # AI 채팅 창 (sidebar, transcript, composer, dialogs)
   └─ widgets/    # 공통 위젯 (card, atmosphere 그라디언트 오브)
```

**핵심 규칙**: `core/` 는 절대 PySide6 를 import 하지 않는다(순수·테스트 가능). `workers/` 만 core 의 로직을 백그라운드 스레드에서 실행하고 결과를 Qt 신호로 UI 에 전달한다.

## 응답성 (스레딩 / 스트리밍)
- 모든 장시간 작업(모델 pull, 채팅 스트리밍, 임베딩, 설치)은 `CancellableWorker`(QRunnable)에서 실행.
- 다운로드는 별도 스레드풀을 써서 채팅을 막지 않음.
- 채팅 토큰은 deque 에 모았다가 UI 의 `QTimer`(~40ms)가 일괄 반영 → 리페인트 폭주 방지.
- **중지**: Ollama 에 취소 API 가 없으므로, 워커가 스트림 연결을 끊어(소켓 close) 생성을 중단.

## 플랫폼별 동작

| 항목 | Windows | macOS |
|---|---|---|
| VRAM 감지 | nvidia-smi → 레지스트리 `qwMemorySize` | Apple Silicon 통합 메모리(RAM×0.7 추정) / Intel `system_profiler` VRAM |
| GPU 이름 | WMI (PowerShell `Get-CimInstance`) | `system_profiler SPDisplaysDataType` |
| Ollama 설치 | winget → OllamaSetup.exe `/VERYSILENT` | `brew install --cask ollama` → 수동 안내 |
| 터미널 실행 | `cmd /k ollama run` | `osascript` → Terminal.app |

> `Win32_VideoController.AdapterRAM` 은 4GB 에서 캡되는 버그가 있어 VRAM 값으로 쓰지 않고 GPU 이름 용도로만 사용.

## Ollama 연동
- Base: `http://127.0.0.1:11434` (localhost 대신 127.0.0.1 — IPv6 지연 회피)
- `GET /api/tags`(설치 목록), `POST /api/pull`(스트림 진행), `POST /api/chat`(스트림+`images` base64), `POST /api/embed`(폴백 `/api/embeddings`), `DELETE /api/delete`
- 공식 `ollama` 패키지 대신 raw `httpx` 사용 — 스트리밍 취소 제어를 위해.

## RAG 파이프라인
1. 문서 로드(txt/md/pdf/docx) → 재귀 문자 분할(~900자, 오버랩 150)
2. Ollama `/api/embed` 로 `nomic-embed-text`(768d) 임베딩 (자동 pull, 배치 처리)
3. sqlite 에 정규화 임베딩 저장 → numpy 행렬곱 코사인 검색 top-k
4. 질의 시 top-k 를 시스템 프롬프트로 주입

## 향후 (이 앱을 엔진으로)
문제집 생성 → 문제 해설 수집 → 요약문서 → 요약+문제집 → 영상화 파이프라인의 로컬 AI 엔진으로 사용 예정.

## 패키징 (향후)
PyInstaller **one-dir** 권장(빠른 시작·AV 오탐 감소). Ollama·모델은 번들하지 않고 런타임 설치. `subprocess` 호출은 `CREATE_NO_WINDOW` 로 콘솔 플래시 방지.
