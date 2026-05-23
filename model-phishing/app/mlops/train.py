"""
Model 1 재학습 스크립트 (Stage 4 - Retrain)
============================================
training_data.csv (2차 수집 신규 피싱) + phiusiil_full.csv (원본)
→ 병합 → RandomForest 재학습 → 신규 모델 .pkl 저장
→ WandB 에 metrics 기록 + 모델 Artifact 업로드
→ training_data.csv 를 archive/ 로 이동 후 빈 파일로 리셋

설계 (기존 합의):
  - 피처 자동선택 안 함. 고정 18개 (기존 모델과 동일).
  - 4-모델 대회 안 함. RandomForest 단일.
  - 신규 데이터만으로 학습하지 않음 — 원본과 병합해야 정상(label=0)이 포함됨.

실행:
  python -m app.mlops.train
  (재학습 여부 판단인 500행 임계값은 GitHub Actions 워크플로우가 담당.
   이 스크립트는 호출되면 무조건 재학습한다.)
"""

import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, roc_auc_score,
)

from app.ml.preprocessor import MODEL_FEATURES

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("model1.train")

# ── 경로 ─────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent   # model-phishing/
DATA_DIR = BASE_DIR / "data"
ARCHIVE_DIR = DATA_DIR / "archive"
ML_DIR = BASE_DIR / "app" / "ml"

TRAINING_CSV = DATA_DIR / "training_data.csv"          # 2차 수집 신규 데이터
ORIGIN_CSV = DATA_DIR / "phiusiil_full.csv"            # 원본 데이터셋
MODEL_PATH = ML_DIR / "phishing_ml_model.pkl"          # 현재 운영 모델
CANDIDATE_PATH = ML_DIR / "phishing_ml_model_candidate.pkl"  # 재학습 산출물

# ── WandB ────────────────────────────────────────────────────────────
WANDB_PROJECT = "secureops-model1-phishing"

# RandomForest 설정 — 기존 모델과 동일하게 고정
RF_PARAMS = dict(n_estimators=100, random_state=42, n_jobs=-1)


def load_merged_dataset() -> pd.DataFrame:
    """원본 + 신규 수집 데이터를 18피처 + label 로 병합."""
    cols = MODEL_FEATURES + ["label"]

    origin = pd.read_csv(ORIGIN_CSV, usecols=cols)
    log.info("원본 데이터: %d행", len(origin))

    if TRAINING_CSV.exists():
        # training_data.csv 는 메타 컬럼(url 등)도 있으므로 18피처+label만 취함
        new_df = pd.read_csv(TRAINING_CSV)
        new_df = new_df[[c for c in cols if c in new_df.columns]]
        log.info("신규 수집 데이터: %d행", len(new_df))
    else:
        new_df = pd.DataFrame(columns=cols)
        log.info("신규 수집 데이터 없음 — 원본만으로 재학습")

    merged = pd.concat([origin, new_df], ignore_index=True)
    # 18피처 전체가 동일한 행은 중복으로 간주해 제거
    merged = merged.drop_duplicates(subset=MODEL_FEATURES).reset_index(drop=True)
    log.info("병합 후(중복 제거): %d행 — label 분포 %s",
             len(merged), merged["label"].value_counts().to_dict())
    return merged


def train(df: pd.DataFrame) -> dict:
    """RandomForest 재학습 → candidate .pkl 저장 → metrics 반환."""
    X = df[MODEL_FEATURES]
    y = df["label"].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # 스케일링 — 학습 데이터로 fit (DataFrame 유지: feature name 보존)
    scaler = StandardScaler()
    X_train_scaled = pd.DataFrame(
        scaler.fit_transform(X_train), columns=MODEL_FEATURES, index=X_train.index
    )
    X_test_scaled = pd.DataFrame(
        scaler.transform(X_test), columns=MODEL_FEATURES, index=X_test.index
    )

    model = RandomForestClassifier(**RF_PARAMS)
    model.fit(X_train_scaled, y_train)

    # 평가
    pred = model.predict(X_test_scaled)
    proba = model.predict_proba(X_test_scaled)[:, 1]
    metrics = {
        "Accuracy": round(accuracy_score(y_test, pred), 4),
        "Precision": round(precision_score(y_test, pred), 4),
        "Recall": round(recall_score(y_test, pred), 4),
        "F1-Score": round(f1_score(y_test, pred), 4),
        "ROC-AUC": round(roc_auc_score(y_test, proba), 4),
    }
    log.info("재학습 완료 — metrics: %s", metrics)

    # 4키 번들로 저장 (기존 phishing_ml_model.pkl 과 동일 구조)
    bundle = {
        "model": model,
        "scaler": scaler,
        "features": MODEL_FEATURES,
        "metrics": metrics,
    }
    joblib.dump(bundle, CANDIDATE_PATH)
    log.info("후보 모델 저장: %s", CANDIDATE_PATH)
    return metrics


def log_to_wandb(metrics: dict, n_rows: int):
    """WandB에 metrics 기록 + 후보 모델을 Artifact로 업로드."""
    try:
        import wandb
    except ImportError:
        log.warning("wandb 미설치 — WandB 기록 건너뜀")
        return

    run = wandb.init(
        project=WANDB_PROJECT,
        job_type="retrain",
        config={"n_estimators": RF_PARAMS["n_estimators"],
                "dataset_rows": n_rows,
                "n_features": len(MODEL_FEATURES)},
    )
    wandb.log(metrics)

    # 모델 레지스트리 — 후보 모델을 버전 관리되는 Artifact로 업로드
    artifact = wandb.Artifact("phishing-model", type="model", metadata=metrics)
    artifact.add_file(str(CANDIDATE_PATH))
    run.log_artifact(artifact)
    run.finish()
    log.info("WandB 기록 완료: project=%s", WANDB_PROJECT)


def archive_training_csv():
    """재학습에 쓴 training_data.csv 를 archive/ 로 이동 후 빈 파일로 리셋.

    → 다음 주기는 0행부터 다시 쌓인다 (중복 재학습 방지).
    """
    if not TRAINING_CSV.exists():
        return
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = ARCHIVE_DIR / f"training_data_{stamp}.csv"

    # 헤더를 보존해 빈 파일로 리셋
    header = TRAINING_CSV.read_text(encoding="utf-8").splitlines()[:1]
    shutil.move(str(TRAINING_CSV), str(dest))
    if header:
        TRAINING_CSV.write_text(header[0] + "\n", encoding="utf-8")
    log.info("training_data.csv 아카이브: %s (이후 0행으로 리셋)", dest)


def main():
    log.info("=" * 55)
    log.info("  Model 1 재학습 시작")
    log.info("=" * 55)

    df = load_merged_dataset()
    metrics = train(df)
    log_to_wandb(metrics, n_rows=len(df))
    archive_training_csv()

    log.info("재학습 파이프라인 완료. 후보 모델: %s", CANDIDATE_PATH)
    log.info("→ 다음 단계: evaluate.py 가 후보 vs 현재 모델을 비교한다.")


if __name__ == "__main__":
    main()