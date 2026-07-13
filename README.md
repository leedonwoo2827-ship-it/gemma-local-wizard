# Auto Gemma Starter

버튼 몇 번으로 내 PC에 나만의 로컬 AI(Google **Gemma**)를 설치하고, 인터넷 없이 채팅까지 할 수 있는 **로컬 AI 데스크톱 GUI 앱**입니다. **Windows · macOS · Linux** 모두 지원하며, 엔진은 [Ollama](https://ollama.com)를 사용합니다.

## 설치 & 실행

### 가장 쉬운 방법 (더블클릭)
- **Windows**: `run.bat` 더블클릭
- **macOS**: 최초 1회 `chmod +x run.command` 후 `run.command` 더블클릭
- **Linux**: 최초 1회 `chmod +x run.sh` 후 `./run.sh` 실행

필요한 라이브러리를 자동 설치한 뒤 앱을 실행합니다. Ollama·모델은 앱 안에서 버튼으로 설치합니다.

### 수동 실행
```bash
pip install -r requirements.txt
python -m auto_gemma.main
```
> Python 3.10+ 필요. Windows 10/11 · macOS(Apple Silicon/Intel) · Linux.

## 주요 기능
- **설치 마법사**: 사양 감지(OS/RAM/VRAM/GPU) → VRAM 기준 추천 모델 → Ollama·Gemma 자동 설치/관리
- **AI 채팅**: 스트리밍 대화, 지식 도서관(RAG), 봇 관리, 이미지 입력, 대화 저장/검색, 내보내기
- **PDF 요약**: 채팅 창의 `PDF 요약` 탭에서 텍스트 복사가 가능한 PDF(또는 txt/md)를 **원문의 10% 또는 5% 분량**으로 요약(긴 책도 구간별로 나눠 처리) → 복사/저장

## 문서 (docs/)
- [설치 가이드](docs/installation.md) — 플랫폼별 상세 설치, 저장 위치 변경, 문제 해결
- [기능 안내](docs/features.md) — 마법사·채팅 전체 기능, 모델 추천 기준, 데이터 저장 위치
- [SQLD 워크플로우 시나리오](docs/workflow-sqld.md) — 스캔→전사→출제→요약→음성/슬라이드 실전 순서
- [아키텍처](docs/architecture.md) — 프로젝트 구조, 플랫폼별 동작, 개발 메모

## 라이선스
MIT
