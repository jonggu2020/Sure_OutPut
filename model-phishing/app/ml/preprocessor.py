"""
피처 전처리기 (PhiUSIIL 18-feature)
===================================
URL → 모델 입력 18개 피처 추출.

phishing_ml_model.pkl 의 features 18개에 정확히 맞춘다:
  [URL 기반 8개]  URL 문자열만으로 계산 — 크롤링 불필요
  [HTML 기반 10개] 페이지를 크롤링해 계산 — PhiUSIIL 논문 표준 정의

설계 원칙:
  - 크롤링 실패(타임아웃/접속불가)해도 예외를 던지지 않는다.
    HTML 피처를 0으로 채운 채 URL 피처만으로라도 추론이 진행되게 한다.
  - 반환 dict의 키와 순서는 MODEL_FEATURES 와 1:1 일치한다.
"""

import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

# 모델이 기대하는 18개 피처 — 순서 고정 (phishing_ml_model.pkl["features"])
MODEL_FEATURES = [
    "URLLength", "NoOfSubDomain", "NoOfLettersInURL", "LetterRatioInURL",
    "NoOfDegitsInURL", "DegitRatioInURL", "NoOfOtherSpecialCharsInURL",
    "SpacialCharRatioInURL", "LineOfCode", "URLTitleMatchScore", "Robots",
    "IsResponsive", "HasSubmitButton", "NoOfImage", "NoOfCSS", "NoOfJS",
    "NoOfSelfRef", "NoOfExternalRef",
]

# 크롤링 설정
_CRAWL_TIMEOUT = 8.0
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}


# ── URL 기반 피처 (8개) — 크롤링 불필요 ──────────────────────────────

def _url_features(url: str) -> dict:
    """URL 문자열만으로 계산하는 8개 피처."""
    parsed = urlparse(url)
    hostname = parsed.hostname or ""

    url_length = len(url)
    letters = sum(c.isalpha() for c in url)
    digits = sum(c.isdigit() for c in url)
    # 영숫자가 아닌 문자 중, 일반 URL 구분자(:/?#[]@!$&'()*+,;=.-_~)를 제외한 '기타' 특수문자
    other_special = sum(
        1 for c in url
        if not c.isalnum() and c not in ":/?#[]@!$&'()*+,;=.-_~"
    )

    # 서브도메인 개수: 호스트명 점 분할에서 도메인+TLD(2) 를 뺀 값
    host_parts = hostname.split(".") if hostname else []
    no_of_subdomain = max(len(host_parts) - 2, 0)

    return {
        "URLLength": float(url_length),
        "NoOfSubDomain": float(no_of_subdomain),
        "NoOfLettersInURL": float(letters),
        "LetterRatioInURL": float(letters / url_length) if url_length else 0.0,
        "NoOfDegitsInURL": float(digits),
        "DegitRatioInURL": float(digits / url_length) if url_length else 0.0,
        "NoOfOtherSpecialCharsInURL": float(other_special),
        "SpacialCharRatioInURL": float(other_special / url_length) if url_length else 0.0,
    }


# ── HTML 기반 피처 (10개) — 크롤링 필요 ──────────────────────────────

def _title_match_score(url: str, title: str) -> float:
    """
    URLTitleMatchScore (0~100): URL과 페이지 title의 문자 일치율.
    PhiUSIIL 정의 근사 — title의 단어들이 URL에 얼마나 포함되는지.
    """
    if not title:
        return 0.0
    host = (urlparse(url).hostname or "").lower().replace("www.", "")
    host_letters = re.sub(r"[^a-z0-9]", "", host)
    title_letters = re.sub(r"[^a-z0-9]", "", title.lower())
    if not title_letters:
        return 0.0
    matched = sum(1 for c in title_letters if c in host_letters)
    return round(matched / len(title_letters) * 100, 2)


async def _html_features(url: str) -> dict:
    """페이지를 크롤링해 계산하는 10개 피처. 실패 시 전부 0."""
    blank = {
        "LineOfCode": 0.0, "URLTitleMatchScore": 0.0, "Robots": 0.0,
        "IsResponsive": 0.0, "HasSubmitButton": 0.0, "NoOfImage": 0.0,
        "NoOfCSS": 0.0, "NoOfJS": 0.0, "NoOfSelfRef": 0.0, "NoOfExternalRef": 0.0,
    }

    try:
        async with httpx.AsyncClient(
            timeout=_CRAWL_TIMEOUT, follow_redirects=True, headers=_HEADERS, verify=False
        ) as client:
            resp = await client.get(url)
            html = resp.text
    except Exception:
        # 크롤링 실패 → HTML 피처는 0으로 두고 URL 피처만으로 추론 진행
        return blank

    soup = BeautifulSoup(html, "html.parser")
    host = (urlparse(url).hostname or "").lower()

    # 링크를 self / external 로 분류
    self_ref, external_ref = 0, 0
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("#") or href.startswith("/") or not href:
            self_ref += 1
        else:
            link_host = (urlparse(href).hostname or "").lower()
            if link_host and host and link_host.endswith(host):
                self_ref += 1
            elif link_host:
                external_ref += 1
            else:
                self_ref += 1

    # 제출 버튼 존재 여부
    has_submit = bool(
        soup.find("button", {"type": "submit"})
        or soup.find("input", {"type": "submit"})
    )
    # 반응형 여부 — viewport 메타태그
    is_responsive = bool(soup.find("meta", {"name": "viewport"}))

    title_tag = soup.find("title")
    title_text = title_tag.get_text(strip=True) if title_tag else ""

    feats = dict(blank)
    feats["LineOfCode"] = float(html.count("\n") + 1)
    feats["URLTitleMatchScore"] = _title_match_score(url, title_text)
    feats["Robots"] = 1.0  # robots 접근 차단 여부는 별도 요청 필요 — 보수적으로 1
    feats["IsResponsive"] = 1.0 if is_responsive else 0.0
    feats["HasSubmitButton"] = 1.0 if has_submit else 0.0
    feats["NoOfImage"] = float(len(soup.find_all("img")))
    feats["NoOfCSS"] = float(len(soup.find_all("link", {"rel": "stylesheet"}))
                             + len(soup.find_all("style")))
    feats["NoOfJS"] = float(len(soup.find_all("script")))
    feats["NoOfSelfRef"] = float(self_ref)
    feats["NoOfExternalRef"] = float(external_ref)
    return feats


# ── 공개 함수 ────────────────────────────────────────────────────────

async def extract_features(url: str) -> dict:
    """
    URL → 18개 피처 dict.

    반환 dict는 MODEL_FEATURES 순서/키와 1:1 일치한다.
    services/predict.py 는 이 dict를 그대로 모델 입력으로 사용한다.
    """
    feats = {}
    feats.update(_url_features(url))
    feats.update(await _html_features(url))
    # MODEL_FEATURES 순서로 정렬 + 누락 키 방어
    return {k: float(feats.get(k, 0.0)) for k in MODEL_FEATURES}