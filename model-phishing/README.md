# Model 1: HTML 피싱 탐지 서버

> 담당: 이종구 | 포트: 8001 | 데이터셋: PhiUSIIL Phishing URL

---

## 현재 상태: ✅ 구현 완료

RandomForest 모델 (18개 피처, 99.9% 정확도) 실서비스 투입 완료.

---

## 실행 방법

```bash
cd model-phishing
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

확인: `✅ 모델 로딩 완료: RandomForestClassifier (피처 18개)`

> ⚠️ `app/ml/phishing_ml_model.pkl` 파일이 있어야 합니다.

---

## 피처 18개

### URL 기반 (8개, 크롤링 불필요)

URLLength, NoOfSubDomain, NoOfLettersInURL, LetterRatioInURL,
NoOfDegitsInURL, DegitRatioInURL, NoOfOtherSpecialCharsInURL, SpacialCharRatioInURL

### HTML 기반 (10개, 페이지 크롤링 후 추출)

LineOfCode, URLTitleMatchScore, Robots, IsResponsive,
HasSubmitButton, NoOfImage, NoOfCSS, NoOfJS, NoOfSelfRef, NoOfExternalRef

---

## 엔드포인트

### POST /predict

```json
// 입력
{"url": "https://example.com"}

// 출력
{
  "is_phishing": false,
  "confidence": 0.12,
  "details": {
    "model_type": "RandomForestClassifier",
    "features_used": 18,
    "phishing_probability": 0.12,
    "normal_probability": 0.88,
    "feature_values": {...}
  }
}
```
