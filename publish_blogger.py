"""posts/ 의 새 마크다운 글을 Blogger에 자동 게시한다.

필요한 환경변수(GitHub Secrets):
    BLOGGER_BLOG_ID, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN

이미 올린 글은 published.json에 기록되어 다시 올리지 않는다.
사용법:  python publish_blogger.py [--limit 3] [--dry-run]
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

import markdown
import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
POSTS_DIR = BASE_DIR / "posts"
PUBLISHED_FILE = BASE_DIR / "published.json"
TOKEN_URL = "https://oauth2.googleapis.com/token"
API_URL = "https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts"


def load_published() -> dict:
    if PUBLISHED_FILE.exists():
        return json.loads(PUBLISHED_FILE.read_text(encoding="utf-8"))
    return {}


def save_published(data: dict) -> None:
    PUBLISHED_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_post(text: str) -> tuple[str, str, list[str]]:
    """(제목, 본문 마크다운, 라벨 목록)을 돌려준다. '# 제목' 줄과 '## 해시태그' 섹션은 본문에서 뺀다."""
    lines = text.strip().splitlines()
    title = "제목 없음"
    if lines and lines[0].startswith("# "):
        title = lines.pop(0)[2:].strip()

    labels: list[str] = []
    body: list[str] = []
    in_tags = False
    for ln in lines:
        if re.match(r"^##\s*해시태그", ln):
            in_tags = True
            continue
        if in_tags:
            if ln.startswith("## "):
                in_tags = False
            else:
                labels += [t.lstrip("#") for t in ln.split() if t.startswith("#") and len(t) > 1]
                continue
        body.append(ln)
    # Blogger 라벨은 합계 200자 제한이 있어 앞쪽 10개만 쓴다.
    return title, "\n".join(body).strip(), labels[:10]


def get_access_token() -> str:
    resp = requests.post(TOKEN_URL, data={
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }, timeout=30)
    if resp.status_code != 200:
        sys.exit(f"토큰 발급 실패({resp.status_code}): {resp.text}\n"
                 "→ README의 '리프레시 토큰이 7일 만에 만료될 때' 항목을 확인하세요.")
    return resp.json()["access_token"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=3, help="한 번에 올릴 최대 글 수 (0=전부)")
    parser.add_argument("--dry-run", action="store_true", help="올리지 않고 대상만 출력")
    args = parser.parse_args()

    load_dotenv(BASE_DIR / ".env")
    published = load_published()
    todo = [p for p in sorted(POSTS_DIR.glob("*.md")) if p.name not in published]
    if args.limit > 0:
        todo = todo[: args.limit]
    print(f"게시 대상 {len(todo)}개")
    if args.dry_run or not todo:
        for p in todo:
            print(" -", p.name)
        return 0

    blog_id = os.environ["BLOGGER_BLOG_ID"]
    headers = {"Authorization": f"Bearer {get_access_token()}"}
    failed = 0
    for path in todo:
        title, body_md, labels = parse_post(path.read_text(encoding="utf-8"))
        html = markdown.markdown(body_md, extensions=["extra", "sane_lists"])
        resp = requests.post(API_URL.format(blog_id=blog_id), headers=headers, timeout=60,
                             json={"title": title, "content": html, "labels": labels})
        if resp.status_code == 200:
            published[path.name] = resp.json().get("url", "")
            save_published(published)  # 하나 올릴 때마다 기록해 중복 게시를 막는다
            print(f"  ✓ {path.name} → {published[path.name]}")
        else:
            failed += 1
            print(f"  ✗ {path.name}: {resp.status_code} {resp.text[:300]}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
