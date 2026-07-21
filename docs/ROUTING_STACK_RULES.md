# 라우팅 스택 규칙

이 프로젝트의 실행 스택은 항상 다음 형태를 유지합니다.

```text
viewer -> router -> ai
```

## viewer

`routing_stack/viewer/`는 공통 UI와 HTTP 서버입니다.

- 특정 router 구현을 직접 import하거나 가정하지 않습니다.
- 모든 router에 대해 항상 같은 payload를 뷰어 서버의 `/api/route`로 보냅니다.
- 뷰어 서버는 해당 요청을 라우터 서버로 프록시합니다.
- router 결정 결과와 AI 실행 결과만 표시합니다.

입력 payload:

```json
{
  "prompt": "사용자 프롬프트",
  "router": "geometric",
  "tier": "fast|balanced|premium",
  "task_type": "",
  "difficulty": "",
  "risk_level": "",
  "evaluation_type": ""
}
```

## router adapter

`routing_stack/adapters/`는 교체 가능한 router adapter 계층입니다.

- 모든 router는 `routing_stack.adapters.contract.RouterAdapter` 계약을 따릅니다.
- router는 `cheap`, `mid`, `premium`, `abstain` 중 하나를 선택합니다.
- router는 실제 Ollama 모델명을 알면 안 됩니다.
- 기존 router 구현체는 adapter로 감싸서 연결합니다.

현재 adapter:

- `routing_stack/adapters/geometric_adapter.py`
- `routing_stack/adapters/quality_utility_adapter.py`

새 router를 추가하려면 adapter를 구현하고 `routing_stack/adapters/registry.py`에 등록합니다.

## ai

`routing_stack/ai/`는 실제 로컬 모델 실행을 담당합니다.

- AI 계층만 `cheap`, `mid`, `premium`에 대응하는 실제 로컬 모델명을 압니다.
- 기본 provider는 Ollama입니다.
- router를 교체해도 모델 실행 계층은 바뀌지 않습니다.

기본 모델 매핑:

```text
cheap   -> qwen3:4b-instruct
mid     -> qwen3:8b
premium -> qwen3:14b
```

## 실행

```powershell
python routing_stack\app\router_server.py --ai mock --port 4100
python routing_stack\app\viewer_server.py --router_server_url http://127.0.0.1:4100 --port 4010
```

Ollama를 사용할 때:

```powershell
python routing_stack\app\router_server.py --ai ollama --port 4100
python routing_stack\app\viewer_server.py --router_server_url http://127.0.0.1:4100 --port 4010
```


