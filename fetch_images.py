"""글 속의 `<!-- pixabay: 영어 검색어 -->` 표시를 Pixabay 무료 일러스트로 바꾼다.

- Pixabay API는 무료(가입 후 API 키)이며, 이미지는 직접 링크하지 않고 내려받아 images/ 에 저장한다.
- 표시가 있는 글에서 그림을 찾으면 `![설명](raw 주소)` 와 출처 한 줄로 바꾼다.
- API 키가 없거나 검색 결과가 없으면 표시를 그대로 둔다(글은 그림 없이 게시된다).

환경변수: PIXABAY_API_KEY
사용법:  python fetch_images.py [--dry-run]
"""
import argparse
import hashlib
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
POSTS_DIR = BASE_DIR / "posts"
IMAGES_DIR = BASE_DIR / "images"
RAW_BASE = "https://raw.githubusercontent.com/kimyunsu1001-tech/auto-blog-generator/main/images/"
API = "https://pixabay.com/api/"
MARKER = re.compile(r"<!--\s*pixabay:\s*([^>]+?)\s*-->")


def search(key: str, query: str) -> dict | None:
    resp = requests.get(API, timeout=30, params={
        "key": key, "q": query, "image_type": "illustration", "orientation": "horizontal",
        "min_width": 1000, "safesearch": "true", "per_page": 5, "lang": "en"})
    if resp.status_code != 200:
        print(f"  ✗ Pixabay 검색 실패({resp.status_code}): {resp.text[:150]}")
        return None
    hits = resp.json().get("hits", [])
    return hits[0] if hits else None


def download(url: str, dest: Path) -> bool:
    resp = requests.get(url, timeout=60)
    if resp.status_code != 200 or len(resp.content) < 5000:
        print(f"  ✗ 이미지 내려받기 실패({resp.status_code})")
        return False
    dest.write_bytes(resp.content)
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    load_dotenv(BASE_DIR / ".env")
    key = os.getenv("PIXABAY_API_KEY", "")

    changed = 0
    for path in sorted(POSTS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        m = MARKER.search(text)
        if not m:
            continue
        query = m.group(1)
        print(f"{path.name}: 그림 검색어 '{query}'")
        if args.dry_run:
            continue
        if not key:
            print("  - PIXABAY_API_KEY가 없어 건너뜁니다.")
            continue
        hit = search(key, query)
        if not hit:
            print("  - 검색 결과가 없어 건너뜁니다.")
            continue
        name = f"pixabay_{hit['id']}_{hashlib.sha1(query.encode()).hexdigest()[:6]}.jpg"
        IMAGES_DIR.mkdir(exist_ok=True)
        if not (IMAGES_DIR / name).exists() and not download(hit["largeImageURL"], IMAGES_DIR / name):
            continue
        alt = f"{query} 일러스트"
        block = (f"![{alt}]({RAW_BASE}{name})\n\n"
                 f"*일러스트: {hit.get('user', 'Pixabay')}, [Pixabay]({hit.get('pageURL', 'https://pixabay.com')})*")
        # 처음 한 번만 치환한다(글당 그림 1개).
        path.write_text(MARKER.sub(lambda _: block, text, count=1), encoding="utf-8")
        print(f"  ✓ {name}")
        changed += 1
    print(f"그림을 넣은 글 {changed}개")
    return 0


if __name__ == "__main__":
    sys.exit(main())
