# Viewer Quick Start

이 문서는 브라우저에서 바로 테스트해보기 위한 최소 실행 방법만 정리합니다.

## 1. 라우터 viewer 실행

라우터가 어떤 모델을 선택하는지 확인하고, 선택된 모델의 답변까지 보고 싶을 때 사용합니다.

터미널 1:

```powershell
python routing_stack\app\router_server.py --ai ollama --port 4100
```

터미널 2:

```powershell
python routing_stack\app\viewer_server.py --router_server_url http://127.0.0.1:4100 --port 4010
```

브라우저:

```text
http://127.0.0.1:4010/
```

## 2. 학습 데이터 viewer 실행

`reviewed_outcome_matrix.csv`를 직접 채우고 싶을 때 사용합니다.

이 viewer는 프롬프트 하나를 입력하면 Ollama의 cheap, mid, premium 모델을 모두 실행합니다. 세 답변을 비교한 뒤 가장 좋은 답변의 `Best & Save`를 누르면 아래 파일에 자동 저장됩니다.

```text
data/router_outcomes/reviewed_outcome_matrix.csv
```

터미널:

```powershell
python routing_stack\app\training_labeler_server.py --ai ollama --port 4120
```

브라우저:

```text
http://127.0.0.1:4120/
```

## 3. Ollama 모델 준비

기본 모델 매핑은 다음과 같습니다.

```text
cheap   -> qwen3:4b-instruct
mid     -> qwen3:8b
premium -> qwen3:14b
```

처음 한 번만 모델을 내려받으면 됩니다.

```powershell
ollama pull qwen3:4b-instruct
ollama pull qwen3:8b
ollama pull qwen3:14b
```

모델 실행이 느려 timeout이 나면 서버 실행 시 timeout을 늘립니다.

```powershell
python routing_stack\app\router_server.py --ai ollama --ai_timeout 240 --port 4100
python routing_stack\app\training_labeler_server.py --ai ollama --ai_timeout 240 --port 4120
```

## 4. Ollama 없이 화면만 확인

Ollama를 아직 준비하지 않았거나 UI만 확인하고 싶으면 `mock` 모드로 실행합니다.

라우터 viewer:

```powershell
python routing_stack\app\router_server.py --ai mock --port 4100
python routing_stack\app\viewer_server.py --router_server_url http://127.0.0.1:4100 --port 4010
```

학습 데이터 viewer:

```powershell
python routing_stack\app\training_labeler_server.py --ai mock --port 4120
```

## 5. 어떤 viewer를 써야 하나

라우팅 결과를 테스트하려면:

```text
http://127.0.0.1:4010/
```

학습용 CSV를 채우려면:

```text
http://127.0.0.1:4120/
```
