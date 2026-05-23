"""
Model 1 평가 게이트 (Stage 4 - Evaluate)
=========================================
재학습 산출물(후보 모델)이 현재 운영 모델보다 나쁘지 않은지 검증한다.

판정:
  - 후보가 현재 모델 이상 → 통과. 후보를 운영 모델로 승격(교체).
  - 후보가 현재 모델보다 하락 → 실패. 종료코드 1 로 빠져나간다.
    → GitHub Actions 워크플로우가 이 종료코드를 보고 승격 단계를 건너뛴다.
    → 나쁜 모델이 운영에 올라가는 것을 자동으로 막는다.

비교 기준:
  공통 holdout(원본 데이터 일부)에서 F1-Score 를 측정해 비교한다.
  후보 F1 이 현재 F1 보다 TOLERANCE 이상 떨어지면 실패로 본다.

실행:
  python -m app.mlops.evaluate
"""

import logging
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score

from app.ml.preprocessor import MODEL_FEATURES

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("model1.evaluate")

# ── 경로 ─────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
ML_DIR = BASE_DIR / "app" / "ml"

ORIGIN_CSV = DATA_DIR / "phiusiil_full.csv"
MODEL_PATH = ML_DIR / "phishing_ml_model.pkl"                  # 현재 운영 모델
CANDIDATE_PATH = ML_DIR / "phishing_ml_model_candidate.pkl"    # 재학습 후보
BACKUP_DIR = ML_DIR / "backup"

WANDB_PROJECT = "secureops-model1-phishing"

# 후보 F1 이 현재 F1 보다 이 값 이상 떨어지면 승격 거부
TOLERANCE = 0.01


def _f1_on_holdout(bundle: dict, X_holdout: pd.DataFrame, y_holdout) -> float:
    """주어진 모델 번들로 holdout F1 측정."""
    model, scaler = bundle["model"], bundle["scaler"]
    X_scaled = pd.DataFrame(
        scaler.transform(X_holdout), columns=MODEL_FEATURES, index=X_holdout.index
    )
    pred = model.predict(X_scaled)
    return f1_score(y_holdout, pred)


def evaluate() -> bool:
    """후보 vs 현재 모델 비교. 후보를 승격해도 되면 True."""
    if not CANDIDATE_PATH.exists():
        log.error("후보 모델 없음: %s — train.py 를 먼저 실행하세요.", CANDIDATE_PATH)
        return False
    if not MODEL_PATH.exists():
        # 현재 모델이 아예 없으면 비교 대상이 없으므로 후보를 그대로 승격
        log.warning("현재 운영 모델 없음 — 후보를 그대로 승격합니다.")
        return True

    # 공통 holdout 구성 — random_state 고정으로 두 모델에 같은 셋 적용
    cols = MODEL_FEATURES + ["label"]
    df = pd.read_csv(ORIGIN_CSV, usecols=cols)
    X, y = df[MODEL_FEATURES], df["label"].astype(int)
    _, X_holdout, _, y_holdout = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    current = joblib.load(MODEL_PATH)
    candidate = joblib.load(CANDIDATE_PATH)

    current_f1 = _f1_on_holdout(current, X_holdout, y_holdout)
    candidate_f1 = _f1_on_holdout(candidate, X_holdout, y_holdout)

    log.info("현재 모델 F1 : %.4f", current_f1)
    log.info("후보 모델 F1 : %.4f", candidate_f1)
    log.info("허용 하락 폭 : %.4f", TOLERANCE)

    passed = candidate_f1 >= current_f1 - TOLERANCE

    # WandB 에 평가 결과 기록
    try:
        import wandb
        run = wandb.init(project=WANDB_PROJECT, job_type="evaluate")
        wandb.log({
            "current_f1": round(current_f1, 4),
            "candidate_f1": round(candidate_f1, 4),
            "gate_passed": int(passed),
        })
        run.finish()
    except ImportError:
        log.warning("wandb 미설치 — 평가 결과 WandB 기록 건너뜀")

    if passed:
        log.info("✅ 평가 통과 — 후보가 현재 모델 수준 이상")
    else:
        log.warning("❌ 평가 실패 — 후보 F1 이 현재보다 %.4f 하락",
                    current_f1 - candidate_f1)
    return passed


def promote():
    """후보를 운영 모델로 승격. 기존 모델은 backup/ 으로 보존."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    # 현재 모델 백업
    if MODEL_PATH.exists():
        backup = BACKUP_DIR / f"phishing_ml_model_{stamp}.pkl"
        shutil.copy2(MODEL_PATH, backup)
        log.info("기존 모델 백업: %s", backup)

    # 후보 → 운영 모델로 교체
    shutil.move(str(CANDIDATE_PATH), str(MODEL_PATH))
    log.info("✅ 후보 모델을 운영 모델로 승격: %s", MODEL_PATH)
    log.info("→ Model 1 서버를 재시작해야 새 모델이 메모리에 로딩됩니다.")


def main():
    log.info("=" * 55)
    log.info("  Model 1 평가 게이트")
    log.info("=" * 55)

    if evaluate():
        promote()
        log.info("재학습 모델이 운영에 반영되었습니다.")
        sys.exit(0)
    else:
        # 종료코드 1 → 워크플로우가 승격 단계를 건너뛴다
        log.warning("후보 모델을 폐기합니다. 운영 모델은 그대로 유지됩니다.")
        if CANDIDATE_PATH.exists():
            CANDIDATE_PATH.unlink()
        sys.exit(1)


if __name__ == "__main__":
    main()