"""
추론 서비스
==========
phishing_ml_model.pkl 로딩 + 18피처 추출 + RandomForest 추론.

추론 후 파이프라인 (피싱으로 판정된 경우):
  추론 → 1차 필터링(도메인 중복 체크) → 통과 시 2차 수집(18피처 CSV 적재)

모델 번들 구조 (joblib dict):
  - model    : RandomForestClassifier
  - scaler   : StandardScaler
  - features : 18개 피처 이름 (순서 고정)
  - metrics  : 학습 당시 성능 지표
"""

import logging
from pathlib import Path

import joblib
import pandas as pd

from app.ml.preprocessor import extract_features, MODEL_FEATURES
from app.filtering import process_phishing_url
from app.collector import collect_training_sample

log = logging.getLogger("model1.predict")

MODEL_PATH = Path(__file__).resolve().parent.parent / "ml" / "phishing_ml_model.pkl"


class PredictionService:
    """HTML 피싱 탐지 추론 서비스."""

    def __init__(self):
        self.model = None
        self.scaler = None
        self.features: list[str] = []
        self.metrics: dict = {}

    def load_model(self, model_path: Path = MODEL_PATH):
        """학습된 모델 번들 로딩. 앱 시작 시 1회 호출."""
        if not model_path.exists():
            raise FileNotFoundError(f"모델 파일 없음: {model_path}")

        bundle = joblib.load(model_path)
        self.model = bundle["model"]
        self.scaler = bundle["scaler"]
        self.features = bundle["features"]
        self.metrics = bundle.get("metrics", {})

        if self.features != MODEL_FEATURES:
            raise ValueError(
                "모델 피처와 preprocessor.MODEL_FEATURES 불일치.\n"
                f"  모델:        {self.features}\n"
                f"  preprocessor: {MODEL_FEATURES}"
            )

        log.info("✅ 모델 로딩 완료: %s (피처 %d개)",
                 type(self.model).__name__, len(self.features))

    async def predict(self, url: str) -> dict:
        """URL → 피처 추출 → 모델 추론 → (피싱이면) 1·2차 수집 → 결과."""
        if self.model is None:
            return {
                "is_phishing": False,
                "confidence": 0.0,
                "details": {"error": "model not loaded"},
            }

        # 1. 18개 피처 추출 (URL 8개 + HTML 크롤링 10개)
        features = await extract_features(url)

        # 2. 모델 입력 — 학습 때와 동일하게 컬럼명이 있는 DataFrame으로 구성
        #    (numpy 배열을 쓰면 StandardScaler가 feature-name 경고를 낸다)
        vector = pd.DataFrame([{f: features[f] for f in self.features}])

        # 3. 스케일링 후 추론
        scaled = self.scaler.transform(vector)
        proba = self.model.predict_proba(scaled)[0]
        phishing_prob = float(proba[1])  # classes_ = [0, 1] → 1 = 피싱
        is_phishing = bool(phishing_prob >= 0.5)

        # 4. 피싱으로 판정된 경우에만 → 1차 필터링 → 2차 수집
        #    추론 결과 반환과 무관한 부가 작업이므로, 실패해도 추론 응답은 정상 반환.
        collected = False
        if is_phishing:
            try:
                is_new_domain = process_phishing_url(url, phishing_prob)
                if is_new_domain:
                    # 1차 통과(신규 도메인) → 이미 추출한 18피처를 그대로 적재
                    collected = collect_training_sample(url, features)
            except Exception as e:
                log.error("1·2차 수집 중 오류 (추론 응답은 정상): %s", e)

        return {
            "is_phishing": is_phishing,
            "confidence": round(phishing_prob, 4),
            "details": {
                "model": type(self.model).__name__,
                "phishing_probability": round(phishing_prob, 4),
                "legitimate_probability": round(float(proba[0]), 4),
                "feature_count": len(self.features),
                "features": features,
                "collected_for_training": collected,  # 2차 수집 적재 여부
            },
        }


prediction_service = PredictionService()