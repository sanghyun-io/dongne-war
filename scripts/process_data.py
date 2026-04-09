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

출력 구조 (동 단위):
  { "서울특별시": { "강남구": { "역삼1동": { "chicken": 100, ... }, "_total": { ... } } } }
"""

import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "scripts" / "raw"
OUTPUT_PATH = PROJECT_ROOT / "src" / "data" / "district_counts.json"

SANGGA_CATEGORY_MAP = {
    "치킨": "chicken",
    "카페": "cafe",
    "편의점": "convenience",
}

SI_GU_CITIES = {
    "고양시", "수원시", "성남시", "안양시", "안산시", "용인시",
    "부천시", "시흥시", "화성시", "청주시", "천안시", "전주시",
    "포항시", "창원시", "김해시", "진주시",
}

ACTIVE_STATUS = {
    "realestate": {"영업중"},
    "pharmacy": {"영업/정상"},
    "pcroom": {"영업/정상"},
}

# 동/읍/면 패턴 (지번주소에서 추출)
DONG_PATTERN = re.compile(
    r"([\w가-힣]+[동읍면리가])\s+[\d-]"
)

# 도로명주소 괄호 안 동 추출 패턴
PAREN_DONG_PATTERN = re.compile(
    r"\(([^)]*[동읍면리가][^)]*)\)"
)

CATEGORIES = ["chicken", "cafe", "convenience", "realestate", "pharmacy", "pcroom"]

MAPPING_FILE = RAW_DIR / "국가데이터처_법정동 연계정보_20250602.csv"

VALID_SIDO = {
    "서울특별시", "부산광역시", "대구광역시", "인천광역시",
    "광주광역시", "대전광역시", "울산광역시", "세종특별자치시",
    "경기도", "강원특별자치도", "충청북도", "충청남도",
    "전북특별자치도", "전라남도", "경상북도", "경상남도",
    "제주특별자치도",
}


# ── 법정동→행정동 매핑 ──────────────────────────────────────────────

def load_legal_to_admin_mapping() -> dict[tuple[str, str, str], str | None]:
    """법정동→행정동 매핑 로드.

    Returns:
        dict[(시도, 시군구, 법정동)] → 행정동 (1:1) or None (1:N)
    """
    if not MAPPING_FILE.exists():
        print(f"  WARN: mapping file not found: {MAPPING_FILE.name}")
        return {}

    from collections import defaultdict
    raw = defaultdict(set)

    with open(MAPPING_FILE, "r", encoding="cp949") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sido = row["시도명"].strip()
            sigungu = row["시군구명"].strip()
            admin_dong = row["행정동명"].strip()
            legal_dong = row["법정동명"].strip()
            if sido and sigungu and admin_dong and legal_dong:
                raw[(sido, sigungu, legal_dong)].add(admin_dong)

    # 1:1 → 행정동 반환, 1:N → None
    mapping = {}
    one_to_one = 0
    one_to_many = 0
    for key, admins in raw.items():
        if len(admins) == 1:
            mapping[key] = next(iter(admins))
            one_to_one += 1
        else:
            mapping[key] = None  # 1:N — 법정동 유지
            one_to_many += 1

    print(f"  Mapping loaded: {one_to_one:,} (1:1) + {one_to_many:,} (1:N)")
    return mapping


def legal_to_admin_dong(
    mapping: dict, sido: str, sigungu: str, legal_dong: str
) -> str:
    """법정동을 행정동으로 변환. 1:N이면 법정동 그대로 반환."""
    result = mapping.get((sido, sigungu, legal_dong))
    if result is not None:
        return result
    return legal_dong  # 1:N or not found → 법정동 유지


def find_sangga_dir() -> Path | None:
    for p in RAW_DIR.iterdir():
        if p.is_dir() and "상가" in p.name:
            return p
    return None


def find_file_by_prefix(prefix: str) -> Path | None:
    for p in RAW_DIR.glob("*.csv"):
        if p.name.startswith(prefix):
            return p
    return None


def find_file_by_keyword(keyword: str) -> Path | None:
    for p in RAW_DIR.glob("*.csv"):
        if keyword in p.name:
            return p
    return None


def read_csv_rows(filepath: Path, encoding: str | None = None):
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
    enc = encodings[0]
    with open(filepath, "r", encoding=enc, errors="replace") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        print(f"  OK {filepath.name} ({enc}+replace, {len(rows):,}rows)")
        return rows


# ── 주소 파싱 ──────────────────────────────────────────────────────

def parse_full_address(jibun: str, doro: str) -> tuple[str, str, str] | None:
    """지번주소 + 도로명주소에서 (시도, 시군구, 동) 추출.

    1순위: 지번주소에서 동 파싱
    2순위: 도로명주소 괄호에서 동 추출
    동을 알 수 없으면 None 반환
    """
    sido, sigungu, dong = "", "", ""

    # 지번주소 파싱 시도
    if jibun and jibun.strip():
        parts = jibun.strip().split()
        if len(parts) >= 3:
            sido = parts[0]
            if "세종" in sido:
                sido = parts[0]
                sigungu = "세종특별자치시"
                # 세종은 시군구 없이 바로 동
                dong_match = DONG_PATTERN.search(jibun)
                if dong_match:
                    dong = dong_match.group(1)
                return (sido, sigungu, dong) if dong else None

            sigungu = parts[1]
            # 시+구 구조
            if sigungu in SI_GU_CITIES and len(parts) >= 4 and parts[2].endswith("구"):
                sigungu = f"{sigungu} {parts[2]}"
                dong_candidate = parts[3]
            else:
                dong_candidate = parts[2]

            # 동/읍/면/리/가 패턴 확인
            if re.match(r"[\w가-힣]+[동읍면리가]$", dong_candidate):
                dong = dong_candidate

    # 지번에서 동을 못 찾으면 도로명 괄호에서 시도
    if not dong and doro and doro.strip():
        # 시도/시군구는 지번에서 얻었으면 유지, 없으면 도로명에서
        if not sido:
            parts = doro.strip().split()
            if len(parts) >= 2:
                sido = parts[0]
                if "세종" in sido:
                    sigungu = "세종특별자치시"
                else:
                    sigungu = parts[1]
                    if sigungu in SI_GU_CITIES and len(parts) >= 3 and parts[2].endswith("구"):
                        sigungu = f"{sigungu} {parts[2]}"

        # 괄호에서 동 추출: "... (역삼동)" 또는 "... (역삼동, 어쩌구빌딩)"
        m = PAREN_DONG_PATTERN.search(doro)
        if m:
            paren_content = m.group(1).strip()
            # 괄호 안에 쉼표가 있으면 첫 번째 토큰이 동
            first_token = paren_content.split(",")[0].strip().split()[0]
            if re.match(r"[\w가-힣]+[동읍면리가]$", first_token):
                dong = first_token

    if sido and sigungu and dong and sido in VALID_SIDO:
        return sido, sigungu, dong
    return None


def parse_sido_sigungu_from_address(address: str) -> tuple[str, str] | None:
    """시군구 레벨까지만 파싱 (동 없이)"""
    if not address or not address.strip():
        return None
    parts = address.strip().split()
    if len(parts) < 2:
        return None
    sido = parts[0]
    if sido not in VALID_SIDO:
        return None
    if "세종" in sido:
        return sido, "세종특별자치시"
    sigungu = parts[1]
    if sigungu in SI_GU_CITIES and len(parts) >= 3 and parts[2].endswith("구"):
        sigungu = f"{sigungu} {parts[2]}"
    return sido, sigungu


# ── 결과 저장 구조 ─────────────────────────────────────────────────

class DongCounter:
    """시도 > 시군구 > 동 > 카테고리별 카운트"""

    def __init__(self):
        self.data = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int))))

    def add(self, sido, sigungu, dong, category):
        self.data[sido][sigungu][dong][category] += 1
        self.data[sido][sigungu]["_total"][category] += 1

    def add_sigungu_only(self, sido, sigungu, category):
        """동을 모를 때 시군구 _total에만 추가"""
        self.data[sido][sigungu]["_total"][category] += 1

    def to_dict(self):
        result = {}
        for sido in sorted(self.data):
            result[sido] = {}
            for sigungu in sorted(self.data[sido]):
                result[sido][sigungu] = {}
                for dong in sorted(self.data[sido][sigungu]):
                    d = {}
                    for cat in CATEGORIES:
                        d[cat] = self.data[sido][sigungu][dong].get(cat, 0)
                    result[sido][sigungu][dong] = d
        return result


# ── 1. 상가(상권)정보 ─────────────────────────────────────────────

def process_sangga(sangga_dir: Path, counter: DongCounter, mapping: dict):
    print("\n[상가정보] 치킨, 카페, 편의점 추출")
    total_rows = 0
    matched = defaultdict(int)
    no_dong = 0
    merged_to_legal = 0

    for csv_file in sorted(sangga_dir.glob("*.csv")):
        rows = read_csv_rows(csv_file, encoding="utf-8")
        total_rows += len(rows)

        for row in rows:
            sub_cat = row.get("상권업종소분류명", "").strip()
            if sub_cat not in SANGGA_CATEGORY_MAP:
                continue

            category = SANGGA_CATEGORY_MAP[sub_cat]
            sido = row.get("시도명", "").strip()
            sigungu = row.get("시군구명", "").strip()
            admin_dong = row.get("행정동명", "").strip()
            legal_dong = row.get("법정동명", "").strip()

            if not sido or not sigungu:
                continue

            if admin_dong:
                # 1:N 매핑인 경우 법정동명 사용 (부동산/약국/PC방과 통합)
                key = (sido, sigungu, legal_dong)
                if legal_dong and key in mapping and mapping[key] is None:
                    # 1:N — 법정동으로 통합
                    counter.add(sido, sigungu, legal_dong, category)
                    merged_to_legal += 1
                else:
                    counter.add(sido, sigungu, admin_dong, category)
            else:
                counter.add_sigungu_only(sido, sigungu, category)
                no_dong += 1
            matched[category] += 1

    print(f"  Total rows: {total_rows:,}")
    for cat, n in matched.items():
        print(f"  {cat}: {n:,}")
    if no_dong:
        print(f"  (dong unknown: {no_dong:,})")
    print(f"  (merged to legal dong: {merged_to_legal:,})")


# ── 2. 부동산중개업 ───────────────────────────────────────────────

def process_realestate(counter: DongCounter, mapping: dict):
    print("\n[부동산] 부동산중개업사무소정보")
    filepath = find_file_by_prefix("AL_D171")
    if not filepath:
        print("  AL_D171_*.csv 파일 없음")
        return

    rows = read_csv_rows(filepath, encoding="euc-kr")
    active = 0
    dong_found = 0

    for row in rows:
        if row.get("상태구분명", "").strip() not in ACTIVE_STATUS["realestate"]:
            continue
        active += 1

        jibun = (row.get("지번주소", "") or "").strip()
        doro = (row.get("도로명주소", "") or "").strip()

        parsed = parse_full_address(jibun, doro)
        if parsed:
            sido, sigungu, dong = parsed
            dong = legal_to_admin_dong(mapping, sido, sigungu, dong)
            counter.add(sido, sigungu, dong, "realestate")
            dong_found += 1
        else:
            # 동 모르면 시군구까지만
            addr = jibun or doro
            sg = parse_sido_sigungu_from_address(addr)
            if sg:
                counter.add_sigungu_only(sg[0], sg[1], "realestate")

    print(f"  Active: {active:,}, dong found: {dong_found:,} ({dong_found/max(active,1)*100:.1f}%)")


# ── 3. 약국 ──────────────────────────────────────────────────────

def process_pharmacy(counter: DongCounter, mapping: dict):
    print("\n[약국] 건강_약국")
    filepath = find_file_by_keyword("약국")
    if not filepath:
        print("  약국 CSV 파일 없음")
        return

    rows = read_csv_rows(filepath)
    active = 0
    dong_found = 0

    for row in rows:
        if row.get("영업상태명", "").strip() not in ACTIVE_STATUS["pharmacy"]:
            continue
        active += 1

        jibun = (row.get("지번주소", "") or "").strip()
        doro = (row.get("도로명주소", "") or "").strip()

        parsed = parse_full_address(jibun, doro)
        if parsed:
            sido, sigungu, dong = parsed
            dong = legal_to_admin_dong(mapping, sido, sigungu, dong)
            counter.add(sido, sigungu, dong, "pharmacy")
            dong_found += 1
        else:
            addr = jibun or doro
            sg = parse_sido_sigungu_from_address(addr)
            if sg:
                counter.add_sigungu_only(sg[0], sg[1], "pharmacy")

    print(f"  Active: {active:,}, dong found: {dong_found:,} ({dong_found/max(active,1)*100:.1f}%)")


# ── 4. PC방 ──────────────────────────────────────────────────────

def process_pcroom(counter: DongCounter, mapping: dict):
    print("\n[PC방] 인터넷컴퓨터게임시설제공업")
    filepath = find_file_by_keyword("인터넷컴퓨터게임시설")
    if not filepath:
        print("  PC방 CSV 파일 없음")
        return

    rows = read_csv_rows(filepath)
    active = 0
    dong_found = 0

    for row in rows:
        if row.get("영업상태명", "").strip() not in ACTIVE_STATUS["pcroom"]:
            continue
        active += 1

        jibun = (row.get("지번주소", "") or "").strip()
        doro = (row.get("도로명주소", "") or "").strip()

        parsed = parse_full_address(jibun, doro)
        if parsed:
            sido, sigungu, dong = parsed
            dong = legal_to_admin_dong(mapping, sido, sigungu, dong)
            counter.add(sido, sigungu, dong, "pcroom")
            dong_found += 1
        else:
            addr = jibun or doro
            sg = parse_sido_sigungu_from_address(addr)
            if sg:
                counter.add_sigungu_only(sg[0], sg[1], "pcroom")

    print(f"  Active: {active:,}, dong found: {dong_found:,} ({dong_found/max(active,1)*100:.1f}%)")


# ── main ──────────────────────────────────────────────────────────

def main():
    print("=" * 50)
    print("dongne-war data preprocessing (dong-level)")
    print("=" * 50)

    if not RAW_DIR.exists():
        print(f"\nERROR: {RAW_DIR} does not exist.")
        sys.exit(1)

    counter = DongCounter()

    # 법정동→행정동 매핑 로드
    print("\n[매핑] 법정동→행정동 변환 테이블")
    mapping = load_legal_to_admin_mapping()

    # 1. 상가정보 → 치킨, 카페, 편의점 (행정동명, 1:N은 법정동으로 통합)
    sangga_dir = find_sangga_dir()
    if sangga_dir:
        process_sangga(sangga_dir, counter, mapping)
    else:
        print("\nWARN: sangga directory not found")

    # 2~4. 부동산, 약국, PC방 (법정동→행정동 변환 적용)
    process_realestate(counter, mapping)
    process_pharmacy(counter, mapping)
    process_pcroom(counter, mapping)

    # 출력
    print("\nBuilding output...")
    result = counter.to_dict()

    sido_count = len(result)
    sigungu_count = sum(len(v) for v in result.values())
    dong_count = sum(
        len(dongs) for sidos in result.values() for dongs in sidos.values()
    )
    print(f"  sido: {sido_count}, sigungu: {sigungu_count}, entries (dong+_total): {dong_count}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    size = OUTPUT_PATH.stat().st_size
    print(f"\nDONE: {OUTPUT_PATH}")
    print(f"  File size: {size:,} bytes ({size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
