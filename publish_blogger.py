"""posts/ 의 새 마크다운 글을 Blogger에 자동 게시한다.

필요한 환경변수(GitHub Secrets):
    BLOGGER_BLOG_ID, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN

이미 올린 글은 published.json에 기록되어 다시 올리지 않는다.
이미 올린 글의 .md 내용이 바뀌면 Blogger의 기존 글을 수정(업데이트)한다.
사용법:  python publish_blogger.py [--limit 3] [--dry-run]
"""
import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

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


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


ISSUE_DIR = BASE_DIR / ".issue_bodies"


def write_issue_body(path: Path, title: str, url: str, text: str) -> None:
    """새 글이 올라가면 네이버·다음 블로그에 직접 올릴 때 복사하기 좋은 이슈 본문을 만든다."""
    ISSUE_DIR.mkdir(exist_ok=True)
    body = (
        f"@kimyunsu1001-tech 새 글이 Blogger에 게시됐어요: {url}\n\n"
        "## 네이버·다음 블로그에 올리는 방법 (직접 붙여넣기)\n"
        "1. 아래 **복사용 본문**을 펼쳐 내용을 드래그해서 복사합니다.\n"
        "2. 네이버/다음 블로그 글쓰기 화면에 붙여넣고 제목을 입력합니다.\n"
        "3. 그림이 있다면 직접 올리고, 해시태그와 카테고리를 확인한 뒤 발행합니다.\n"
        "4. 올린 뒤 이 이슈를 닫아 주세요.\n\n"
        "> 같은 글을 여러 곳에 그대로 올리면 검색에서 중복 문서로 취급될 수 있다는 이야기가 있어요"
        "(확인된 정보는 아니에요). 가능하면 서론과 결론을 조금 바꿔서 올려 보세요.\n\n"
        f"<details><summary>복사용 본문 펼치기</summary>\n\n{text}\n\n</details>\n"
    )
    (ISSUE_DIR / f"{path.stem}.md").write_text(body, encoding="utf-8")
    (ISSUE_DIR / f"{path.stem}.title").write_text(f"[네이버·다음 업로드] {title}", encoding="utf-8")


def normalize(entry) -> dict:
    """예전 형식(주소 문자열)과 새 형식({url,id,hash})을 모두 받아 dict로 통일한다."""
    if isinstance(entry, str):
        return {"url": entry, "id": "", "hash": ""}
    return entry


def find_post_id(headers: dict, blog_id: str, url: str) -> str:
    """게시 주소로 Blogger 글 ID를 찾는다(예전 기록에는 ID가 없어서)."""
    path = urlparse(url).path
    resp = requests.get(API_URL.format(blog_id=blog_id) + "/bypath",
                        headers=headers, params={"path": path}, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"글 ID 조회 실패({resp.status_code}): {resp.text[:200]}")
    return resp.json()["id"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=3, help="한 번에 처리할 최대 글 수 (0=전부)")
    parser.add_argument("--dry-run", action="store_true", help="올리지 않고 대상만 출력")
    args = parser.parse_args()

    load_dotenv(BASE_DIR / ".env")
    published = {k: normalize(v) for k, v in load_published().items()}

    todo = []  # (path, text, 'new' | 'update')
    for p in sorted(POSTS_DIR.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        entry = published.get(p.name)
        if entry is None:
            todo.append((p, text, "new"))
        elif entry.get("hash") and entry["hash"] != content_hash(text):
            todo.append((p, text, "update"))
        elif not entry.get("hash"):
            # 예전 기록(해시 없음): 지금 내용을 기준으로 기록만 채워 둔다. 단, 이번 실행에서 수정 대상이 된다.
            todo.append((p, text, "update"))
    if args.limit > 0:
        todo = todo[: args.limit]
    print(f"처리 대상 {len(todo)}개")
    for p, _, mode in todo:
        print(f" - [{mode}] {p.name}")
    if args.dry_run or not todo:
        return 0

    blog_id = os.environ["BLOGGER_BLOG_ID"]
    headers = {"Authorization": f"Bearer {get_access_token()}"}
    failed = 0
    for path, text, mode in todo:
        title, body_md, labels = parse_post(text)
        html = markdown.markdown(body_md, extensions=["extra", "sane_lists"])
        payload = {"title": title, "content": html, "labels": labels}
        try:
            if mode == "new":
                resp = requests.post(API_URL.format(blog_id=blog_id), headers=headers,
                                     timeout=60, json=payload)
            else:
                entry = published[path.name]
                post_id = entry.get("id") or find_post_id(headers, blog_id, entry["url"])
                resp = requests.patch(f"{API_URL.format(blog_id=blog_id)}/{post_id}",
                                      headers=headers, timeout=60, json=payload)
        except RuntimeError as e:
            failed += 1
            print(f"  ✗ {path.name}: {e}")
            continue
        if resp.status_code == 200:
            data = resp.json()
            published[path.name] = {"url": data.get("url", ""), "id": data.get("id", ""),
                                    "hash": content_hash(text)}
            save_published(published)  # 하나 처리할 때마다 기록해 중복 게시를 막는다
            print(f"  ✓ {mode} {path.name} → {data.get('url', '')}")
            if mode == "new":
                write_issue_body(path, title, data.get("url", ""), body_md)
        else:
            failed += 1
            print(f"  ✗ {mode} {path.name}: {resp.status_code} {resp.text[:300]}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
