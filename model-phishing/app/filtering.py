"""
1차 필터링 (Stage 1)
====================
피싱으로 탐지된 URL을 받아, 주요 도메인 기준으로 중복을 거른다.

역할:
  - URL → 주요 등록 도메인 추출 (m.bokjiro.go.kr → bokjiro.go.kr)
  - 이미 본 도메인이면 → 필터링 (반환 False)
  - 처음 보는 도메인이면 → filter_1st_domains.csv 에 기록하고 반환 True

반환값의 의미:
  True  = 처음 보는 피싱 도메인 → 2차 수집(18피처 추출)으로 진행
  False = 이미 아는 도메인 → 여기서 중단

filter_1st_domains.csv 는 "지금까지 본 피싱 도메인 색인"이다.
재학습용 데이터가 아니라 중복 판단용 키 목록이다.
재학습 데이터(18피처)는 2차 수집의 training_data.csv 가 담당한다.
"""

import csv
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

import tldextract

log = logging.getLogger("model1.filter1")

# ── 저장 위치 ────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FILTER_CSV = DATA_DIR / "filter_1st_domains.csv"

CSV_COLUMNS = ["domain", "first_seen", "phishing_probability", "sample_url"]

# CSV 동시 쓰기 보호 (FastAPI는 여러 요청을 동시에 처리할 수 있다)
_lock = threading.Lock()

# tldextract 인스턴스 — 공인 접미사 목록(PSL) 기반 도메인 분리.
# 한 번 생성해 재사용한다. (suffix_list_urls=None 으로 두면 내장 스냅샷 사용)
_extractor = tldextract.TLDExtract()


def extract_main_domain(url: str) -> str | None:
    """
    URL → 주요 등록 도메인.

    예:
      https://m.bokjiro.go.kr/ssis-tem/index.do → bokjiro.go.kr
      https://claude.ai/chat/abc                → claude.ai
      https://www.naver.com                     → naver.com

    도메인을 뽑을 수 없으면 None (예: IP 주소, 잘못된 URL).
    """
    ext = _extractor(url)
    # ext.domain = 등록 이름, ext.suffix = 공인 접미사(co.kr, com 등)
    if not ext.domain or not ext.suffix:
        return None
    return f"{ext.domain}.{ext.suffix}".lower()


def _load_seen_domains() -> set[str]:
    """filter_1st_domains.csv 에서 이미 기록된 도메인 집합을 읽는다."""
    if not FILTER_CSV.exists():
        return set()
    seen = set()
    try:
        with FILTER_CSV.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                d = (row.get("domain") or "").strip()
                if d:
                    seen.add(d)
    except Exception as e:
        log.error("1차 필터 CSV 읽기 실패: %s", e)
    return seen


def _ensure_csv_header():
    """CSV 파일이 없으면 헤더만 있는 빈 파일을 만든다."""
    if FILTER_CSV.exists():
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with FILTER_CSV.open("w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerow(CSV_COLUMNS)


def process_phishing_url(url: str, phishing_probability: float) -> bool:
    """
    피싱으로 탐지된 URL을 1차 필터링한다.

    Args:
        url: 피싱으로 판정된 전체 URL
        phishing_probability: 모델이 낸 피싱 확률 (0~1)

    Returns:
        True  → 처음 보는 도메인. CSV에 기록했고, 2차 수집으로 진행해야 함.
        False → 이미 아는 도메인이거나 도메인 추출 실패. 여기서 중단.
    """
    domain = extract_main_domain(url)
    if domain is None:
        log.info("1차 필터: 도메인 추출 실패 — 건너뜀 (%s)", url[:60])
        return False

    # 읽기-판정-쓰기를 하나의 임계구역으로 묶어, 동시 요청 시
    # 같은 도메인이 두 번 기록되는 경쟁 상태를 막는다.
    with _lock:
        _ensure_csv_header()
        seen = _load_seen_domains()

        if domain in seen:
            log.info("1차 필터: 중복 도메인 — 필터링 (%s)", domain)
            return False

        # 처음 보는 도메인 → CSV에 한 줄 추가
        row = [
            domain,
            datetime.now(timezone.utc).isoformat(),
            round(float(phishing_probability), 4),
            url,
        ]
        with FILTER_CSV.open("a", encoding="utf-8", newline="") as f:
            csv.writer(f).writerow(row)

        log.info("1차 필터: 신규 피싱 도메인 기록 — %s (p=%.4f)",
                 domain, phishing_probability)
        return True


def is_known_phishing_domain(url: str) -> bool:
    """
    임의의 URL이 '이미 알려진 피싱 도메인'에 속하는지 조회한다.

    사용자가 검사한 URL의 도메인이 1차 필터 CSV에 있으면 True.
    → 모델 추론 없이도 "이미 아는 피싱 사이트"로 즉시 판단할 수 있다.
    """
    domain = extract_main_domain(url)
    if domain is None:
        return False
    with _lock:
        return domain in _load_seen_domains()