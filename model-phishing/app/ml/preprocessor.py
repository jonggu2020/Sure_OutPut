"""
피처 전처리기
============
URL에서 모델 입력 피처를 추출.
PhiUSIIL 논문 기반 피처 엔지니어링.
"""

from urllib.parse import urlparse


async def extract_features(url: str) -> dict:
    """
    URL → 피처 딕셔너리 변환.

    추출 피처:
    - URL 패턴: 길이, 특수문자 수, 서브도메인 깊이
    - HTML 구조: TODO (실제 페이지 크롤링 후)
    - Domain WHOIS: TODO (whois API 연동)
    - VirusTotal: TODO (VT API 연동)
    """
    parsed = urlparse(url)

    features = {
        # URL 기반 피처
        "url_length": len(url),
        "hostname_length": len(parsed.hostname or ""),
        "path_length": len(parsed.path),
        "num_dots": url.count("."),
        "num_hyphens": url.count("-"),
        "num_underscores": url.count("_"),
        "num_slashes": url.count("/"),
        "num_query_params": len(parsed.query.split("&")) if parsed.query else 0,
        "has_https": 1 if parsed.scheme == "https" else 0,
        "has_ip_address": _has_ip_address(parsed.hostname or ""),
        "subdomain_depth": len((parsed.hostname or "").split(".")) - 2,
        "has_at_symbol": 1 if "@" in url else 0,

        # TODO: HTML 구조 피처 (크롤링 후 추가)
        # "num_forms": 0,
        # "num_iframes": 0,
        # "has_password_field": 0,

        # TODO: WHOIS 피처
        # "domain_age_days": 0,
        # "registrar": "",

        # TODO: VirusTotal 스코어
        # "vt_score": 0,
    }

    return features


def _has_ip_address(hostname: str) -> int:
    """호스트명이 IP 주소인지 확인."""
    parts = hostname.split(".")
    if len(parts) == 4:
        try:
            return 1 if all(0 <= int(p) <= 255 for p in parts) else 0
        except ValueError:
            return 0
    return 0
