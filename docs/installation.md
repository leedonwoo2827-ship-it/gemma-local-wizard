# 설치 가이드

## 요구 사항
- **OS**: Windows 10/11 또는 macOS (Apple Silicon/Intel)
- **Python**: 3.10 이상
- **Ollama**: 앱이 자동 설치 (Windows: winget/설치파일, macOS: Homebrew)

## 1. 앱 실행

### Windows
1. `run.bat` 더블클릭
2. 필요한 라이브러리가 자동 설치되고 앱이 실행됩니다.

수동 실행:
```powershell
pip install -r requirements.txt
python -m auto_gemma.main
```

### macOS
1. 터미널에서 최초 1회 실행 권한 부여:
   ```bash
   chmod +x run.command
   ```
2. `run.command` 더블클릭 (또는 터미널에서 `./run.command`)

수동 실행:
```bash
pip3 install -r requirements.txt
python3 -m auto_gemma.main
```

## 2. Ollama 설치 (앱 내부 버튼)

앱을 실행하면 **2. Ollama** 섹션에서 상태를 확인하고 **"Ollama 설치"** 버튼으로 자동 설치합니다.

### Windows
1. **winget** 으로 설치 시도 (`Ollama.Ollama`, 사용자 설치 — 관리자 권한 불필요)
2. winget 이 없거나 실패하면 **OllamaSetup.exe** 를 내려받아 무음 설치(`/VERYSILENT`)
3. 설치 후 `http://127.0.0.1:11434/api/version` 폴링으로 성공 확인

### macOS
1. **Homebrew** 가 있으면 `brew install --cask ollama` 실행 후 `ollama serve` 로 엔진 기동
2. Homebrew 가 없으면 자동 설치 불가 → <https://ollama.com/download/mac> 에서 **Ollama.app** 을 직접 내려받아 설치

## 3. 모델 설치

**3. Gemma 모델 선택 및 관리** 에서 모델을 고르고 **"설치"** 를 누르면 다운로드가 진행됩니다(진행률 표시). Ollama 가 아직 없으면 설치까지 자동으로 처리합니다.

저사양 PC(통합 그래픽/VRAM 낮음)에서는 `gemma3:1b`(디스크 ~0.8GB, RAM 2GB+)가 자동 추천됩니다.

## 문제 해결

| 증상 | 원인 / 해결 |
|---|---|
| "설치되어 있지 않습니다" 가 계속 표시 | Ollama 서버 미기동. 앱이 `ollama serve` 를 자동 실행하지만, 안 되면 직접 실행하거나 재설치 |
| winget 을 찾을 수 없음 | 구형/LTSC Windows. 앱이 자동으로 설치 파일 방식으로 폴백 |
| 모델 다운로드가 느림 | 모델 용량(1b~17GB)에 따라 시간이 걸립니다. 진행률 확인 |
| VRAM 이 "감지 안됨(통합 추정)" | 통합 그래픽(예: Intel Iris Xe). 정상 — CPU/부분 가속으로 `gemma3:1b` 추천 |
| 채팅이 응답하지 않음 | 모델이 아직 설치 안 됨 → 모델 설치 후 채팅 창의 모델 선택 확인 |
| macOS 자동 설치 실패 | Homebrew 미설치. 위 2번의 수동 다운로드 방법 사용 |

## 데이터 위치
대화/지식도서관 데이터는 `내 문서/GemmaChat/` 아래에 저장됩니다(삭제해도 앱 동작에는 지장 없음).
