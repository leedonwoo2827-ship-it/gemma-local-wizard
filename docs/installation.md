# 설치 가이드

## 요구 사항
- **OS**: Windows 10/11 · macOS (Apple Silicon/Intel) · Linux
- **Python**: 3.10 이상
- **Ollama**: 설치 및 실행 중 ([ollama.com](https://ollama.com))
- **Gemma 모델**: `ollama pull gemma3:4b` 등으로 미리 준비

## 1. Ollama & 모델 준비
```bash
# Ollama 설치 후 (ollama.com), 모델 다운로드
ollama pull gemma3:4b
```
앱은 Ollama 가 실행 중이라고 가정합니다. 미실행 상태로 앱을 켜면, 설치돼 있는 경우 `ollama serve` 를 자동으로 시작 시도합니다.

## 2. 앱 실행

### Windows
1. `run.bat` 더블클릭 → 라이브러리 자동 설치 후 실행

수동 실행:
```powershell
pip install -r requirements.txt
python -m auto_gemma.main
```

### macOS
```bash
chmod +x run.command   # 최초 1회
./run.command
```

### Linux
```bash
chmod +x run.sh        # 최초 1회
./run.sh
```

수동 실행(공통):
```bash
pip3 install -r requirements.txt
python3 -m auto_gemma.main
```

## 문제 해결

| 증상 | 원인 / 해결 |
|---|---|
| 상단바에 "× Ollama 없음/응답 없음" | Ollama 미실행. 직접 `ollama serve` 실행 후 [새로고침] |
| 모델 목록이 `gemma3:4b` 하나뿐 | 설치된 gemma 모델이 없음. `ollama pull gemma3:4b` 실행 후 [새로고침] |
| PDF 요약 결과가 비어 있음/오류 | 스캔 이미지 PDF 라 텍스트가 추출되지 않음. 텍스트 복사가 되는 PDF 사용 |
| 요약이 오래 걸림 | 문서가 길수록 구간 수가 많아 시간이 걸립니다. 진행률 확인, 필요 시 [중지] |
| 채팅이 응답하지 않음 | 모델 미선택/미설치 → 상단바 모델 선택 확인 |

## 데이터 위치
대화 데이터는 `내 문서/GemmaChat/conversations/` 아래에 저장됩니다(삭제해도 앱 동작에는 지장 없음).
