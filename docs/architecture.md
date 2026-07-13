# 아키텍처

## 프로젝트 구조

```
auto_gemma/
├─ main.py        # 진입점 (QApplication 부트스트랩, 테마, MainWindow)
├─ app/           # config(경로·모델 카탈로그·상수), theme(라이트 QSS/팔레트)
├─ core/          # 순수 로직 (Qt 비의존 — 테스트 가능)
│  ├─ ollama_client.py   # httpx: version/tags/pull(stream)/chat(stream)
│  ├─ summarizer.py      # 구간(청크)별 요약 → 이어붙이는 map 방식 요약
│  ├─ rag/               # loaders(txt/md/pdf), chunker (요약 청크 분할에 사용)
│  └─ persistence/       # conversations (JSON)
├─ workers/       # QRunnable 워커 (core ↔ Qt 신호 브리지, 취소 가능)
└─ ui/            # PySide6 UI
   ├─ main_window.py  # 상단바(모델/Ollama 상태) + 탭
   ├─ chat/       # 채팅 위젯 (sidebar, transcript, composer, dialogs)
   ├─ summary/    # PDF 요약 위젯
   └─ widgets/    # 공통 위젯 (card, 스레드풀)
```

**핵심 규칙**: `core/` 는 절대 PySide6 를 import 하지 않는다(순수·테스트 가능). `workers/` 만 core 의 로직을 백그라운드 스레드에서 실행하고 결과를 Qt 신호로 UI 에 전달한다.

## 응답성 (스레딩 / 스트리밍)
- 장시간 작업(채팅 스트리밍, PDF 요약)은 `CancellableWorker`(QRunnable)에서 실행 → UI 안 멈춤.
- 스트리밍 토큰은 deque 에 모았다가 UI 의 `QTimer`(~40ms)가 일괄 반영 → 리페인트 폭주 방지.
- **중지**: Ollama 에 취소 API 가 없으므로, 워커가 스트림 연결을 끊어(소켓 close) 생성을 중단.

## Ollama 연동
- Base: `http://127.0.0.1:11434` (localhost 대신 127.0.0.1 — IPv6 지연 회피)
- `GET /api/version`(상태), `GET /api/tags`(설치 목록), `POST /api/chat`(스트림), `POST /api/pull`(폴백 다운로드)
- 공식 `ollama` 패키지 대신 raw `httpx` 사용 — 스트리밍 취소 제어를 위해.
- Ollama 미실행 시 설치돼 있으면 `ollama serve` 를 백그라운드로 시작 시도.

## 요약 파이프라인 (`core/summarizer.py`)
1. `loaders.load_text()` 로 PDF/txt/md → 순수 텍스트 (pypdf `extract_text`).
2. `chunker.chunk_text()` 로 ~8000자 구간(청크)으로 분할.
3. 각 구간을 `client.chat()` 로 `약 len(chunk)×ratio 자` 분량으로 요약.
4. 구간 요약을 이어 붙여 반환 → 전체가 대략 원문의 10% / 5% 분량.
- 구간별 요약이라 수백 페이지 책도 컨텍스트 한계 없이 처리. 진행률·중지 지원.

## 향후 (이 앱을 기본으로)
이 저장소는 앞으로 확장할 로컬 AI 도구의 **기본(base)** 이다. 요약 결과를 바탕으로 문제집 생성·해설·영상화 등으로 확장할 수 있다.
