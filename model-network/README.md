# Model 2: 네트워크 로그 분석 서버

> 담당: 서용준 | 포트: 8002 | 데이터셋: CIC-Bell-DNS 2021

---

## 이 서버가 하는 일

샌드박스 Docker 컨테이너에서 자동 수집된 네트워크 트래픽 데이터를 받아서, 악성 여부를 판별합니다.

```
[샌드박스 Docker]
  └─ network_agent.py (5초마다 자동 수집)
       └─ Gateway /api/sandbox/network-data
            └─ 이 서버 /predict (여기서 분석)
                 └─ 결과 반환 → 대시보드에 표시
```

사용자가 샌드박스에서 브라우저를 사용하는 동안, 백그라운드에서 자동으로 이 서버에 데이터가 들어옵니다.
별도로 데이터를 수집하거나 전송하는 코드를 짤 필요 없습니다.

---

## 실행 방법

```bash
cd model-network
python -m venv .venv

# Windows
.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8002
```

http://localhost:8002/docs 에서 Swagger UI 확인.

---

## 필수 구현 엔드포인트

### GET /health

Gateway 헬스체크용. 이미 구현되어 있음. 수정 불필요.

```json
// 응답
{"status": "ok", "model": "network-log"}
```

### POST /predict

**이 엔드포인트를 실제 모델 추론으로 교체하면 됩니다.**

#### 입력 (자동으로 들어오는 데이터)

```json
{
  "sandbox_id": "secureops-sandbox-6081",
  "log_data": {
    "sandbox_id": "secureops-sandbox-6081",
    "timestamp": 1234567890.0,
    "packet_count": 150,
    "bytes_sent": 24000,
    "bytes_received": 180000,
    "request_frequency": 12.5,
    "unique_domains": 5,
    "dns_query_count": 3,
    "avg_packet_size": 1360.0,
    "protocol_distribution": {"TCP": 0.85, "UDP": 0.15},
    "connection_count": 8,
    "suspicious_ports": 0
  }
}
```

#### 입력 필드 상세

| 필드 | 타입 | 설명 | 위협 판단 힌트 |
|------|------|------|---------------|
| packet_count | int | 수집 기간(5초) 내 패킷 수 | 급증 → DDoS/스캐닝 |
| bytes_sent | int | 송신 바이트 | 대량 송신 → 데이터 유출 |
| bytes_received | int | 수신 바이트 | 대량 수신 → 악성 다운로드 |
| request_frequency | float | 초당 요청 수 | 50+ → 비정상 |
| unique_domains | int | 접속한 고유 IP 수 | 다수 → C2 통신 의심 |
| dns_query_count | int | DNS 쿼리 수 | 급증 → DNS 터널링 |
| avg_packet_size | float | 평균 패킷 크기 (bytes) | 극소/극대 → 비정상 |
| protocol_distribution | dict | TCP/UDP 비율 | UDP 과다 → 터널링 의심 |
| connection_count | int | 활성 연결 수 | 다수 → 봇넷 의심 |
| suspicious_ports | int | 비표준 포트 사용 수 | 1+ → 백도어 의심 |

비표준 포트 = 80, 443, 53, 8080, 8443 이외의 포트.

#### 출력 (Gateway가 이 형태를 기대함)

```json
{
  "is_malicious": false,
  "confidence": 0.15,
  "threat_type": null,
  "details": null
}
```

#### 출력 필드 상세

| 필드 | 타입 | 설명 |
|------|------|------|
| is_malicious | bool | 악성 여부 |
| confidence | float | 0.0 ~ 1.0 신뢰도 |
| threat_type | str or null | "phishing", "malware", "c2", "data_exfil", "dns_tunnel" 등 |
| details | dict or null | 추가 정보 (판단 근거, feature importance 등) |

---

## 수정해야 하는 파일

### app/main.py — `/predict` 엔드포인트

현재 더미 응답을 반환하고 있습니다. 이 부분을 실제 모델로 교체하세요:

```python
# 현재 (더미)
if suspicious > 3 or high_frequency:
    return PredictResponse(is_malicious=True, ...)

# 교체 후 (실제 모델)
features = extract_features(log)           # log_data에서 피처 추출
prediction = model.predict(features)       # XGBoost/LightGBM 추론
probability = model.predict_proba(features)
return PredictResponse(
    is_malicious=bool(prediction),
    confidence=float(probability[1]),
    threat_type=classify_threat(prediction, features),
    details={"feature_importance": ...},
)
```

### 추가 생성 권장 파일

```
model-network/
├── app/
│   ├── main.py              ← 수정 (더미 → 실제 모델)
│   ├── services/
│   │   └── predict.py       ← 신규 (추론 로직 분리)
│   └── ml/
│       ├── preprocessor.py  ← 신규 (피처 추출)
│       └── network_model.pkl ← 신규 (학습된 모델)
```

---

## 모델 개발 가이드

### 데이터셋

- CIC 공개 보안 데이터셋 + CIC-Bell-DNS 2021
- 약 225만+ 레코드 (캐나다 사이버보안연구소)
- 정상/악성 트래픽, 피싱 유형 포함

### 모델 후보

Logistic Regression → Random Forest → XGBoost/LightGBM 순서로 비교.
최종 모델은 성능이 가장 좋은 것을 선택.

### 평가 지표

| 지표 | 중요도 | 설명 |
|------|--------|------|
| Recall | ★★★ | 악성 트래픽 탐지율 (놓치면 안 됨) |
| F1-Score | ★★★ | 정밀도-재현율 균형 |
| ROC-AUC | ★★ | 전체 분류 성능 |

### 전처리 참고

- 결측치 처리, 인코딩, 정규화
- 클래스 불균형 보정 (SMOTE 또는 class_weight)
- StandardScaler 적용

---

## 테스트 방법

### 서버 단독 테스트

```bash
# 서버 실행 상태에서
curl -X POST http://localhost:8002/predict \
  -H "Content-Type: application/json" \
  -d '{"sandbox_id":"test","log_data":{"packet_count":150,"bytes_sent":24000,"bytes_received":180000,"request_frequency":12.5,"unique_domains":5,"dns_query_count":3,"avg_packet_size":1360,"protocol_distribution":{"TCP":0.85,"UDP":0.15},"connection_count":8,"suspicious_ports":0}}'
```

### Gateway 연동 테스트

1. Gateway (8000) + 이 서버 (8002) 동시 실행
2. 대시보드에서 URL 검사 → 샌드박스 모드 진입
3. 이 서버 콘솔에 `/predict` 요청이 5초마다 들어오는지 확인
4. Gateway 콘솔에 `network-data 200 OK` 확인

---

## WandB 연동

```python
import wandb

wandb.init(project="secureops-network")
wandb.log({
    "accuracy": accuracy,
    "recall": recall,
    "f1_score": f1,
    "roc_auc": roc_auc,
})
wandb.finish()
```

---

## 주의사항

- 이 서버는 Gateway를 import하지 않습니다. HTTP API로만 통신합니다.
- 다른 팀원의 코드를 건드릴 필요 없습니다. 이 디렉토리 안에서만 작업하세요.
- `/health`와 `/predict` 두 엔드포인트만 정상 동작하면 전체 시스템과 연동됩니다.
