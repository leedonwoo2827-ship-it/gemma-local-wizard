# Auto Gemma Starter

버튼 몇 번으로 내 PC에 나만의 로컬 AI(Google **Gemma**)를 설치하고, 인터넷 없이 채팅까지 할 수 있는 Windows 데스크톱 앱입니다. 엔진은 [Ollama](https://ollama.com)를 사용합니다.

> 유튜브 데모(로컬 AI 설치 무료앱 Auto Gemma Starter)를 참고해 Python + PySide6로 재구현한 버전입니다.

## 주요 기능

### 1) 설치 마법사
- **내 컴퓨터 사양 감지**: OS / RAM / VRAM / GPU 자동 인식
- **VRAM 기준 추천 모델**: 예) VRAM 8GB → `gemma3:4b` (GPU 가속), 제한 요인 표시
- **Ollama 자동 설치**: winget → 설치 파일 폴백
- **Gemma 모델 관리**: 설치 / 업데이트 / 삭제 / 터미널 실행 (다운로드 진행률 표시)

### 2) AI 채팅 (앱 내장 · Docker 불필요)
- 로컬 Gemma와 **스트리밍 대화** (전송 / 중지 / 재생성)
- **지식 도서관 (RAG)**: txt·md·pdf·docx 업로드 → 근거 기반 답변
- **봇 관리**: 커스텀 시스템 프롬프트/페르소나
- **이미지 입력**: 멀티모달 (gemma3 4B/12B/27B)
- **대화 관리**: 새 대화 / 검색 / 이름변경 / 삭제, 자동 저장
- **프롬프트 템플릿**, **고급 설정**(temperature 등), **내보내기**(md/txt)

## 요구 사항
- Windows 10/11, Python 3.10+
- (Ollama는 앱이 자동 설치)

## 설치 & 실행
```bash
pip install -r requirements.txt
python -m auto_gemma.main
```

## 모델 추천 기준 (VRAM)
| VRAM | 추천 모델 |
|---|---|
| < 4GB / 통합 | gemma3:1b |
| 4–11GB | gemma3:4b |
| 12–23GB | gemma3:12b |
| ≥ 24GB | gemma3:27b |

RAM이 부족하면 한 단계 낮은 모델을 추천하고 "제한 요인: RAM"으로 표시합니다.

## 데이터 저장 위치
대화/지식도서관 데이터는 `내 문서/GemmaChat/` 아래에 저장됩니다.

## 프로젝트 구조
```
auto_gemma/
├─ core/         # 순수 로직 (Qt 비의존): ollama_client, installer, system_info, recommend, rag, persistence
├─ workers/      # QRunnable 워커 (core ↔ Qt 신호 브리지)
├─ ui/           # PySide6 UI (wizard, chat, widgets)
└─ app/          # config, theme
```

## 라이선스
MIT
