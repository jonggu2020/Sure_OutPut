"""
추론 서비스
==========
ML 모델 로딩 + 피처 추출 + 추론 파이프라인.
모델은 ml/ 디렉토리에서 로드.
"""

from app.ml.preprocessor import extract_features


class PredictionService:
    """HTML 피싱 탐지 추론 서비스."""

    def __init__(self):
        self.model = None  # 앱 시작 시 로딩

    def load_model(self, model_path: str = "app/ml/model.pkl"):
        """학습된 모델 로딩."""
        # TODO: joblib.load(model_path)
        pass

    async def predict(self, url: str) -> dict:
        """
        URL → 피처 추출 → 모델 추론 → 결과 반환.

        파이프라인:
        1. extract_features(url) → URL 패턴, HTML 구조, WHOIS 등
        2. model.predict(features) → 피싱 여부
        3. model.predict_proba(features) → 확률값
        """
        # 피처 추출
        features = await extract_features(url)

        # TODO: 실제 모델 추론 (프로토타입은 더미 응답)
        # prediction = self.model.predict(features)
        # probability = self.model.predict_proba(features)

        # 더미 응답 (프로토타입)
        return {
            "is_phishing": False,
            "confidence": 0.12,
            "details": {
                "url_length": len(url),
                "has_https": url.startswith("https"),
                "features_extracted": len(features) if features else 0,
            },
        }


prediction_service = PredictionService()
