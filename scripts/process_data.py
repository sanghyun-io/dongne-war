"""
동네전쟁 — data.go.kr CSV 전처리 스크립트

Usage:
    python scripts/process_data.py

Input:  scripts/raw/ (업종별 원본 CSV)
Output: src/data/district_counts.json

데이터 소스:
  1. 소상공인_상가(상권)정보 (시도별 CSV) → 치킨, 카페, 편의점
  2. 부동산중개업사무소정보 (AL_D171_*.csv) → 부동산
  3. 건강_약국.csv → 약국
  4. 문화_인터넷컴퓨터게임시설제공업.csv → PC방
"""

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "scripts" / "raw"
OUTPUT_PATH = PROJECT_ROOT / "src" / "data" / "district_counts.json"

# ── 상가정보: 상권업종소분류명 → 카테고리 매핑 ────────────────────
SANGGA_CATEGORY_MAP = {
    "치킨": "chicken",
    "카페": "cafe",
    "편의점": "convenience",
}

# ── 부동산/약국/PC방: 영업중 필터 값 ─────────────────────────────
ACTIVE_STATUS = {
    "realestate": {"영업중"},
    "pharmacy": {"영업/정상"},
    "pcroom": {"영업/정상"},
}


def find_sangga_dir() -> Path | None:
    """상가(상권)정보 폴더 찾기 (이름에 '상가' 포함된 디렉토리)"""
    for p in RAW_DIR.iterdir():
        if p.is_dir() and "상가" in p.name:
            return p
    return None


def find_file_by_prefix(prefix: str) -> Path | None:
    """RAW_DIR에서 prefix로 시작하는 CSV 파일 찾기"""
    for p in RAW_DIR.glob("*.csv"):
        if p.name.startswith(prefix):
            return p
    return None


def find_file_by_keyword(keyword: str) -> Path | None:
    """RAW_DIR에서 keyword를 포함하는 CSV 파일 찾기"""
    for p in RAW_DIR.glob("*.csv"):
        if keyword in p.name:
            return p
    return None


def read_csv_rows(filepath: Path, encoding: str | None = None):
    """CSV를 DictReader로 읽기. 인코딩 자동 감지."""
    encodings = [encoding] if encoding else ["utf-8", "utf-8-sig", "cp949", "euc-kr"]
    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                print(f"  OK {filepath.name} ({enc}, {len(rows):,}rows)")
                return rows
        except (UnicodeDecodeError, UnicodeError):
            continue
    # 최후 수단: errors=replace로 읽기
    enc = encodings[0]
    with open(filepath, "r", encoding=enc, errors="replace") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        print(f"  OK {filepath.name} ({enc}+replace, {len(rows):,}rows)")
        return rows


def parse_sido_sigungu_from_address(address: str) -> tuple[str, str] | None:
    """주소 문자열에서 시도/시군구 파싱"""
    if not address or not address.strip():
        return None
    parts = address.strip().split()
    if len(parts) < 2:
        return None
    sido = parts[0]
    sigungu = parts[1]
    # 세종특별자치시 예외
    if "세종" in sido:
        return sido, "세종시"
    return sido, sigungu


# ── 1. 상가(상권)정보 처리 ─────────────────────────────────────────

def process_sangga(sangga_dir: Path) -> dict[str, dict]:
    """상가정보 시도별 CSV → 치킨/카페/편의점 시군구별 카운트"""
    print("\n[상가정보] 치킨, 카페, 편의점 추출")

    counts = {cat: defaultdict(lambda: defaultdict(int)) for cat in SANGGA_CATEGORY_MAP.values()}
    total_rows = 0
    matched = defaultdict(int)

    csv_files = sorted(sangga_dir.glob("*.csv"))
    if not csv_files:
        print("  CSV 파일 없음")
        return {}

    for csv_file in csv_files:
        rows = read_csv_rows(csv_file, encoding="utf-8")
        total_rows += len(rows)

        for row in rows:
            sub_cat = row.get("상권업종소분류명", "").strip()
            if sub_cat not in SANGGA_CATEGORY_MAP:
                continue

            category = SANGGA_CATEGORY_MAP[sub_cat]
            sido = row.get("시도명", "").strip()
            sigungu = row.get("시군구명", "").strip()

            if not sido or not sigungu:
                continue

            counts[category][sido][sigungu] += 1
            matched[category] += 1

    print(f"  Total rows: {total_rows:,}")
    for cat, n in matched.items():
        print(f"  {cat}: {n:,}")

    # defaultdict → dict 변환
    result = {}
    for cat, sido_dict in counts.items():
        result[cat] = {sido: dict(sigungu_dict) for sido, sigungu_dict in sido_dict.items()}
    return result


# ── 2. 부동산중개업 처리 ───────────────────────────────────────────

def process_realestate() -> dict:
    """부동산중개업사무소정보 → 시군구별 카운트"""
    print("\n[부동산] 부동산중개업사무소정보")

    filepath = find_file_by_prefix("AL_D171")
    if not filepath:
        print("  AL_D171_*.csv 파일 없음")
        return {}

    rows = read_csv_rows(filepath, encoding="euc-kr")
    counts = defaultdict(lambda: defaultdict(int))
    active = 0

    for row in rows:
        status = row.get("상태구분명", "").strip()
        if status not in ACTIVE_STATUS["realestate"]:
            continue
        active += 1

        # 법정동명에서 시도/시군구 파싱
        addr = row.get("도로명주소", "") or row.get("지번주소", "") or row.get("법정동명", "")
        parsed = parse_sido_sigungu_from_address(addr)
        if not parsed:
            continue
        sido, sigungu = parsed
        counts[sido][sigungu] += 1

    print(f"  Active: {active:,}")
    return {sido: dict(sg) for sido, sg in counts.items()}


# ── 3. 약국 처리 ──────────────────────────────────────────────────

def process_pharmacy() -> dict:
    """약국 → 시군구별 카운트"""
    print("\n[약국] 건강_약국")

    filepath = find_file_by_keyword("약국")
    if not filepath:
        print("  약국 CSV 파일 없음")
        return {}

    rows = read_csv_rows(filepath)
    counts = defaultdict(lambda: defaultdict(int))
    active = 0

    for row in rows:
        status = row.get("영업상태명", "").strip()
        if status not in ACTIVE_STATUS["pharmacy"]:
            continue
        active += 1

        addr = row.get("도로명주소", "") or row.get("지번주소", "")
        parsed = parse_sido_sigungu_from_address(addr)
        if not parsed:
            continue
        sido, sigungu = parsed
        counts[sido][sigungu] += 1

    print(f"  Active: {active:,}")
    return {sido: dict(sg) for sido, sg in counts.items()}


# ── 4. PC방 처리 ──────────────────────────────────────────────────

def process_pcroom() -> dict:
    """인터넷컴퓨터게임시설제공업 → 시군구별 카운트"""
    print("\n[PC방] 인터넷컴퓨터게임시설제공업")

    filepath = find_file_by_keyword("인터넷컴퓨터게임시설")
    if not filepath:
        print("  PC방 CSV 파일 없음")
        return {}

    rows = read_csv_rows(filepath)
    counts = defaultdict(lambda: defaultdict(int))
    active = 0

    for row in rows:
        status = row.get("영업상태명", "").strip()
        if status not in ACTIVE_STATUS["pcroom"]:
            continue
        active += 1

        addr = row.get("도로명주소", "") or row.get("지번주소", "")
        parsed = parse_sido_sigungu_from_address(addr)
        if not parsed:
            continue
        sido, sigungu = parsed
        counts[sido][sigungu] += 1

    print(f"  Active: {active:,}")
    return {sido: dict(sg) for sido, sg in counts.items()}


# ── 병합 & 출력 ───────────────────────────────────────────────────

def merge_results(all_counts: dict[str, dict]) -> dict:
    """모든 업종 결과를 하나의 JSON 구조로 병합"""
    all_keys = set()
    for category_counts in all_counts.values():
        for sido, sigungu_dict in category_counts.items():
            for sigungu in sigungu_dict:
                all_keys.add((sido, sigungu))

    result = {}
    for sido, sigungu in sorted(all_keys):
        if sido not in result:
            result[sido] = {}
        result[sido][sigungu] = {}
        for category, category_counts in all_counts.items():
            count = category_counts.get(sido, {}).get(sigungu, 0)
            result[sido][sigungu][category] = count

    return result


def main():
    print("=" * 50)
    print("dongne-war data preprocessing")
    print("=" * 50)

    if not RAW_DIR.exists():
        print(f"\nERROR: {RAW_DIR} does not exist.")
        print("See scripts/README.md for download instructions.")
        sys.exit(1)

    all_counts = {}

    # 1. 상가정보 → 치킨, 카페, 편의점
    sangga_dir = find_sangga_dir()
    if sangga_dir:
        sangga_counts = process_sangga(sangga_dir)
        for cat in ["chicken", "cafe", "convenience"]:
            all_counts[cat] = sangga_counts.get(cat, {})
    else:
        print("\nWARN: sangga directory not found — chicken/cafe/convenience will be empty")
        for cat in ["chicken", "cafe", "convenience"]:
            all_counts[cat] = {}

    # 2. 부동산
    all_counts["realestate"] = process_realestate()

    # 3. 약국
    all_counts["pharmacy"] = process_pharmacy()

    # 4. PC방
    all_counts["pcroom"] = process_pcroom()

    # 병합
    print("\nMerging...")
    result = merge_results(all_counts)

    sido_count = len(result)
    sigungu_count = sum(len(v) for v in result.values())
    print(f"  sido: {sido_count}, sigungu: {sigungu_count}")

    # 저장
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\nDONE: {OUTPUT_PATH}")
    print(f"  File size: {OUTPUT_PATH.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
