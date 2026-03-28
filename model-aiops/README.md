# Model 3: AIOps 리소스 이상 탐지 서버

> 담당: 차인택 | 포트: 8003 | 관리자 전용

---

## 이 서버가 하는 일

Docker 컨테이너들의 리소스를 모니터링하고, 이상을 탐지하고, 자동으로 대응 조치를 결정합니다.

```
[Prometheus/cAdvisor] → 이 서버가 메트릭 수집
  → Isolation Forest + LSTM 이상 탐지
  → ChromaDB RAG (과거 조치 이력 검색)
  → Ollama LLM (자동 의사결정)
  → Gateway /api/sandbox/pool/config 호출 (Pool 크기 자동 조정)
```

이 서버의 핵심 가치: **사람이 수동으로 하던 Docker 리소스 관리를 AI가 자동화.**

---

## 실행 방법

```bash
cd model-aiops
python -m venv .venv

# Windows
.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8003
```

http://localhost:8003/docs 에서 Swagger UI 확인.

---

## 사용 가능한 인프라

Docker Compose로 실행 시 자동으로 올라가는 서비스들:

| 서비스 | Docker 내부 주소 | 로컬 주소 | 용도 |
|--------|-----------------|-----------|------|
| Prometheus | http://prometheus:9090 | http://localhost:9090 | 메트릭 수집/쿼리 |
| cAdvisor | http://cadvisor:8080 | http://localhost:8085 | Docker 컨테이너 메트릭 |
| Ollama | http://ollama:11434 | http://localhost:11434 | 로컬 LLM 추론 |
| ChromaDB | http://chromadb:8000 | http://localhost:8004 | 벡터 DB (RAG) |

---

## 필수 구현 엔드포인트 (4개)

### 1. GET /health

Gateway 헬스체크용. 이미 구현됨. 수정 불필요.

```json
{"status": "ok", "model": "aiops-resource"}
```

### 2. GET /status — 리소스 상태 조회

Gateway `/api/aiops/status`에서 호출. 관리자 대시보드에 표시됨.

#### 출력

```json
{
  "containers": [
    {
      "container_name": "secureops-sandbox-6081",
      "cpu_percent": 15.2,
      "memory_percent": 42.5,
      "memory_usage_mb": 218.0,
      "network_rx_bytes": 1024000,
      "network_tx_bytes": 512000,
      "disk_read_bytes": 0,
      "disk_write_bytes": 0,
      "is_anomaly": false
    }
  ],
  "total_cpu_percent": 15.2,
  "total_memory_percent": 42.5,
  "anomaly_count": 0,
  "pool_recommendation": "maintain"
}
```

#### 수정 방법

Prometheus API로 실제 메트릭을 수집하도록 교체:

```python
# Prometheus 쿼리 예시
async with httpx.AsyncClient() as client:
    response = await client.get(
        "http://localhost:9090/api/v1/query",
        params={"query": 'rate(container_cpu_usage_seconds_total{name=~"secureops.*"}[1m]) * 100'}
    )
    cpu_data = response.json()
```

### 3. GET /anomalies — 이상 탐지 목록

Gateway `/api/aiops/anomalies`에서 호출.

#### 출력

```json
[
  {
    "container_name": "secureops-sandbox-6081",
    "anomaly_type": "cpu_spike",
    "severity": "high",
    "metric_value": 95.3,
    "threshold": 80.0,
    "detected_at": 1234567890.0,
    "recommended_action": "컨테이너 리소스 제한 또는 종료 권장"
  }
]
```

#### anomaly_type 종류

| 타입 | 설명 | 정상 기준 |
|------|------|----------|
| cpu_spike | CPU 급등 | < 80% |
| memory_leak | 메모리 지속 증가 | < 85% |
| network_flood | 네트워크 트래픽 폭증 | 상대적 판단 |
| disk_exhaustion | 디스크 과다 사용 | < 90% |

#### severity 레벨

| 레벨 | 기준 |
|------|------|
| low | 기준 약간 초과 |
| medium | 지속적 초과 |
| high | 급격한 변화 |
| critical | 즉시 조치 필요 |

### 4. POST /sandbox-policy — 샌드박스 정책 결정

Gateway `/api/aiops/sandbox-policy/{id}`에서 호출.

#### 입력

```json
{
  "sandbox_id": "secureops-sandbox-6081"
}
```

#### 출력

```json
{
  "sandbox_id": "secureops-sandbox-6081",
  "max_lifetime_minutes": 30,
  "action": "extend",
  "reason": "CPU 25%, 메모리 40% — 리소스 여유. 과거 유사 사례에서 60분 연장 성공.",
  "pool_size_recommendation": 7
}
```

#### action 종류

| 액션 | 설명 | 트리거 조건 |
|------|------|-----------|
| maintain | 현재 상태 유지 | 리소스 정상 |
| extend | 수명 연장 | 리소스 여유 |
| scale_down | 리소스 할당 축소 | 약간 부족 |
| terminate | 즉시 종료 | 이상 감지 또는 리소스 심각 부족 |

---

## 수정해야 하는 파일

### app/main.py

모든 엔드포인트의 `# TODO: 차인택` 부분을 실제 로직으로 교체.

### 추가 생성 권장 파일

```
model-aiops/
├── app/
│   ├── main.py                  ← 수정 (더미 → 실제 로직)
│   ├── services/
│   │   ├── metrics_collector.py ← 신규 (Prometheus 메트릭 수집)
│   │   ├── anomaly_detector.py  ← 신규 (Isolation Forest + LSTM)
│   │   ├── rag_engine.py        ← 신규 (ChromaDB RAG)
│   │   └── decision_maker.py    ← 신규 (Ollama LLM 의사결정)
│   └── ml/
│       ├── isolation_forest.pkl ← 신규 (학습된 이상 탐지 모델)
│       └── lstm_model.pt        ← 신규 (시계열 모델)
```

---

## AIOps 파이프라인 구현 가이드

### 1단계: Prometheus 메트릭 수집

```python
# metrics_collector.py
import httpx

PROMETHEUS_URL = "http://localhost:9090"

async def get_container_cpu():
    """컨테이너별 CPU 사용률 수집."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={
                "query": 'rate(container_cpu_usage_seconds_total{name=~"secureops.*"}[1m]) * 100'
            }
        )
        data = response.json()
        # data["data"]["result"] → [{metric: {name: ...}, value: [timestamp, "15.2"]}, ...]
        return data

async def get_container_memory():
    """컨테이너별 메모리 사용량 수집."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={
                "query": 'container_memory_usage_bytes{name=~"secureops.*"}'
            }
        )
        return response.json()
```

### 2단계: 이상 탐지 (Isolation Forest + LSTM)

```python
# anomaly_detector.py
from sklearn.ensemble import IsolationForest
import numpy as np

class AnomalyDetector:
    def __init__(self):
        self.model = IsolationForest(contamination=0.1, random_state=42)

    def fit(self, X):
        """정상 데이터로 학습."""
        self.model.fit(X)

    def predict(self, metrics):
        """
        입력: [cpu_percent, memory_percent, network_rx, network_tx, disk_read, disk_write]
        출력: 1 (정상) or -1 (이상)
        """
        features = np.array([[
            metrics["cpu_percent"],
            metrics["memory_percent"],
            metrics["network_rx_bytes"],
            metrics["network_tx_bytes"],
            metrics["disk_read_bytes"],
            metrics["disk_write_bytes"],
        ]])
        return self.model.predict(features)[0]
```

### 3단계: RAG (ChromaDB)

```python
# rag_engine.py
import chromadb

class RAGEngine:
    def __init__(self):
        self.client = chromadb.HttpClient(host="localhost", port=8004)
        self.collection = self.client.get_or_create_collection("aiops_history")

    def add_action_history(self, situation, action, result):
        """과거 조치 이력 저장."""
        self.collection.add(
            documents=[f"상황: {situation}. 조치: {action}. 결과: {result}"],
            ids=[f"history_{int(time.time())}"],
        )

    def search_similar(self, current_situation, n_results=3):
        """유사 상황의 과거 조치 검색."""
        results = self.collection.query(
            query_texts=[current_situation],
            n_results=n_results,
        )
        return results["documents"]
```

### 4단계: LLM 의사결정 (Ollama)

```python
# decision_maker.py
import requests

OLLAMA_URL = "http://localhost:11434"

def decide_action(metrics, rag_results):
    """LLM에게 조치를 결정하게 함."""
    prompt = f"""
    당신은 Docker 컨테이너 리소스 관리 AI입니다.

    현재 상태:
    - CPU 사용률: {metrics['cpu_percent']}%
    - 메모리 사용률: {metrics['memory_percent']}%
    - 활성 컨테이너: {metrics['container_count']}개
    - 이상 감지: {metrics['anomaly_count']}건

    과거 유사 사례:
    {rag_results}

    다음 중 하나를 선택하고 이유를 설명하세요:
    1. maintain (현재 유지)
    2. extend (샌드박스 수명 연장)
    3. scale_down (리소스 축소)
    4. terminate (즉시 종료)

    추가로 적정 Pool 크기를 추천하세요 (현재: 5).

    JSON 형태로 응답: {{"action": "...", "reason": "...", "pool_size": N}}
    """

    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": "llama3.2", "prompt": prompt, "stream": False}
    )
    return response.json()["response"]
```

### 5단계: 자동 조정 (Gateway Pool 크기 변경)

```python
# Gateway Pool 크기 자동 조정 호출
async with httpx.AsyncClient() as client:
    await client.put(
        "http://localhost:8000/api/sandbox/pool/config",
        json={"pool_size": recommended_size},
        headers={"Authorization": "Bearer ADMIN_TOKEN"},
    )
```

---

## 데이터셋 생성 가이드

Docker Stats API + Prometheus + cAdvisor에서 직접 수집.

### 정상 시나리오 4종

| 시나리오 | CPU | 메모리 | 네트워크 | 설명 |
|---------|-----|--------|---------|------|
| 일반 브라우징 | 5~15% | 20~40% | 낮음 | 뉴스 읽기, 검색 |
| 파일 다운로드 | 10~20% | 30~50% | 높음(수신) | 대용량 파일 |
| 영상 스트리밍 | 15~30% | 40~60% | 높음(수신) | YouTube 등 |
| 다중 탭 | 20~40% | 50~70% | 중간 | 여러 사이트 동시 |

### 이상 시나리오 5종

| 시나리오 | CPU | 메모리 | 네트워크 | 설명 |
|---------|-----|--------|---------|------|
| 크립토마이닝 | 90%+ | 보통 | 보통 | CPU 급등 |
| 메모리 릭 | 보통 | 지속 증가 | 보통 | 악성 스크립트 |
| DDoS/C2 | 보통 | 보통 | 급증(송신) | 봇넷 통신 |
| 랜섬웨어 | 높음 | 높음 | 보통 | 디스크 과다 쓰기 |
| 복합 이상 | 높음 | 높음 | 높음 | 여러 지표 동시 |

### 데이터 수집 방법

```bash
# Docker Stats API로 직접 수집
docker stats --format "{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.NetIO}},{{.BlockIO}}" --no-stream

# 또는 Prometheus 쿼리로 시계열 수집
curl "http://localhost:9090/api/v1/query_range?query=container_cpu_usage_seconds_total&start=2025-01-01T00:00:00Z&end=2025-01-01T01:00:00Z&step=15s"
```

---

## 평가 지표

| 지표 | 중요도 | 설명 |
|------|--------|------|
| F1-Score (이상 탐지) | ★★★ | 이상/정상 분류 균형 |
| RAG 검색 정확도 | ★★ | 유사 사례 매칭 품질 |
| 응답 Latency | ★★ | 의사결정 속도 (5초 이내 목표) |
| Pool 조정 정확도 | ★ | 적정 크기 추천의 적절성 |

---

## WandB 연동

```python
import wandb

wandb.init(project="secureops-aiops")
wandb.log({
    "f1_score": f1,
    "anomaly_detection_accuracy": accuracy,
    "rag_relevance": relevance_score,
    "llm_response_time": latency,
})
wandb.finish()
```

---

## 테스트 방법

### 서버 단독 테스트

```bash
# 리소스 상태 조회
curl http://localhost:8003/status

# 이상 탐지 목록
curl http://localhost:8003/anomalies

# 샌드박스 정책 결정
curl -X POST http://localhost:8003/sandbox-policy \
  -H "Content-Type: application/json" \
  -d '{"sandbox_id": "secureops-sandbox-6081"}'

# Pool 자동 조정
curl -X POST http://localhost:8003/auto-adjust
```

### Gateway 연동 테스트

1. Gateway (8000) + 이 서버 (8003) 동시 실행
2. admin / admin123 으로 로그인
3. 관리자 패널에서 리소스 상태 / Pool 관리 확인

---

## 주의사항

- 이 서버는 관리자 전용입니다. 일반 사용자는 접근할 수 없습니다.
- Gateway를 import하지 않습니다. HTTP API로만 통신합니다.
- Ollama는 로컬에서 실행해야 합니다: `ollama serve` → `ollama pull llama3.2`
- 이 디렉토리 안에서만 작업하세요. 다른 팀원 코드를 건드릴 필요 없습니다.
