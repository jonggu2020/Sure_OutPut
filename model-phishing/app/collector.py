"""
2차 수집 (Stage 2)
==================
1차 필터링을 통과한(= 처음 보는 피싱 도메인) URL에 대해,
18개 피처를 재학습용 데이터셋 training_data.csv 에 적재한다.

핵심:
  - 피처를 새로 추출하지 않는다. 추론(1단계)에서 이미 뽑은 18개를 그대로 받는다.
    → 같은 URL을 두 번 크롤링하지 않는다.
  - CSV 컬럼은 phiusiil_full.csv 와 호환된다.
    → 4단계 재학습에서 원본 데이터셋과 그대로 합칠 수 있다.
  - label 은 전부 1 (피싱). 이 모듈은 피싱 탐지된 URL만 받는다.
    ※ 모델 오탐이 섞일 수 있다 — 추후 인터셉터 행동 기반 라벨 보정 여지를 둔다.

스키마 (길 B):
  [18 피처]  URLLength ... NoOfExternalRef   ← 재학습이 실제 사용
  label                                      ← 전부 1
  [메타]     url, domain, collected_at        ← 재학습 시 무시, 추적/검수용
"""

import csv
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

from app.ml.preprocessor import MODEL_FEATURES
from app.filtering import extract_main_domain

log = logging.getLogger("model1.collect2")

# ── 저장 위치 ────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TRAINING_CSV = DATA_DIR / "training_data.csv"

# CSV 컬럼: 18피처 + label + 메타 3개  (phiusiil_full.csv 와 피처/label 컬럼명 일치)
CSV_COLUMNS = MODEL_FEATURES + ["label", "url", "domain", "collected_at"]

# CSV 동시 쓰기 보호
_lock = threading.Lock()


def _ensure_csv_header():
    """training_data.csv 가 없으면 헤더만 있는 빈 파일을 만든다."""
    if TRAINING_CSV.exists():
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with TRAINING_CSV.open("w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow(CSV_COLUMNS)


def collect_training_sample(url: str, features: dict) -> bool:
    """
    1차 통과한 피싱 URL의 18피처를 재학습 데이터셋에 적재한다.

    Args:
        url:      피싱으로 탐지되고 1차 필터를 통과한 URL
        features: 추론(1단계)에서 이미 추출한 18개 피처 dict.
                  predict 결과의 details["features"] 를 그대로 넘기면 된다.

    Returns:
        True  → training_data.csv 에 정상 적재됨
        False → 피처 누락 등으로 적재 실패
    """
    # 18개 피처가 모두 있는지 검증 — 하나라도 빠지면 학습 데이터가 깨진다
    missing = [f for f in MODEL_FEATURES if f not in features]
    if missing:
        log.error("2차 수집 실패: 피처 누락 %s (%s)", missing, url[:60])
        return False

    domain = extract_main_domain(url) or ""

    # 행 구성 — CSV_COLUMNS 순서 그대로
    row = {f: features[f] for f in MODEL_FEATURES}
    row["label"] = 1                       # 피싱 탐지된 URL만 받으므로 전부 1
    row["url"] = url
    row["domain"] = domain
    row["collected_at"] = datetime.now(timezone.utc).isoformat()

    with _lock:
        _ensure_csv_header()
        with TRAINING_CSV.open("a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            writer.writerow(row)

    log.info("2차 수집: 학습 샘플 적재 — %s (domain=%s)", url[:50], domain)
    return True


def count_collected_samples() -> int:
    """현재까지 모인 재학습 샘플 수 (헤더 제외). 4단계 재학습 트리거 판단용."""
    if not TRAINING_CSV.exists():
        return 0
    with _lock:
        with TRAINING_CSV.open("r", encoding="utf-8", newline="") as f:
            return max(sum(1 for _ in f) - 1, 0)