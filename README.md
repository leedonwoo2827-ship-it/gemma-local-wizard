# Gemma PDF 요약 & 채팅

로컬 Gemma(Google) 모델로 **PDF 문서를 요약**하고 **채팅**할 수 있는 간단한 데스크톱 GUI 앱입니다.
엔진은 [Ollama](https://ollama.com)를 사용하며, **Gemma3 가 이미 설치되어 실행되는 PC**를 전제로 합니다.

- **PDF 요약**: 텍스트 복사가 가능한 PDF(예: 기본서 복붙 PDF)를 **원문의 10% 또는 5% 분량**으로 요약. 긴 책도 구간별로 나눠 요약한 뒤 이어 붙입니다.
- **AI 채팅**: 스트리밍 대화 + 대화 저장/불러오기/검색/내보내기.

> 스캔 이미지 PDF 는 텍스트가 추출되지 않아 요약할 수 없습니다. **텍스트 선택·복사가 되는 PDF**를 사용하세요.

## 사전 준비
1. [Ollama](https://ollama.com) 설치 및 실행
2. Gemma 모델 준비 (없으면 터미널에서):
   ```bash
   ollama pull gemma3:4b
   ```

## 설치 & 실행

### 가장 쉬운 방법 (더블클릭)
- **Windows**: `run.bat` 더블클릭
- **macOS**: 최초 1회 `chmod +x run.command` 후 `run.command` 더블클릭
- **Linux**: 최초 1회 `chmod +x run.sh` 후 `./run.sh` 실행

필요한 라이브러리를 자동 설치한 뒤 앱을 실행합니다.

### 수동 실행
```bash
pip install -r requirements.txt
python -m auto_gemma.main
```
> Python 3.10+ 필요. Windows 10/11 · macOS(Apple Silicon/Intel) · Linux.

## 사용법
1. 상단바에서 **모델**을 선택합니다(설치된 `gemma*` 모델 자동 감지).
2. **[PDF 요약]** 탭: `PDF 선택` → `10% / 5%` 선택 → `요약 시작`. 진행률이 표시되고, 끝나면 결과를 복사하거나 파일로 저장할 수 있습니다.
3. **[채팅]** 탭: 메시지를 입력해 Gemma 와 대화합니다. 대화는 자동 저장되어 왼쪽 목록에서 다시 열 수 있습니다.

## 문서 (docs/)
- [설치 가이드](docs/installation.md)
- [기능 안내](docs/features.md)
- [아키텍처](docs/architecture.md)

## 라이선스
MIT
