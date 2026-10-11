"""Gemini 무료 API로 블로그 글 초안을 자동 생성하는 스크립트.

사용법:
    python generator.py              # 아직 안 쓴 키워드 1개 처리 (기본값)
    python generator.py --limit 3    # 최대 3개 처리
    python generator.py --limit 0    # 남은 키워드 전부 처리
"""
import argparse
import os
import re
import sys
import time
from datetime import date
from pathlib import Path

import google.generativeai as genai
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
KEYWORDS_FILE = BASE_DIR / "keywords.txt"
POSTS_DIR = BASE_DIR / "posts"

# 무료 티어는 분당 요청 수 제한이 있어 요청 사이에 쉬어 준다.
DELAY_SECONDS = 5
MAX_RETRIES = 3

PROMPT_TEMPLATE = """당신은 SEO에 능숙한 한국어 블로그 전문 작가입니다.
아래 키워드로 검색 상위 노출을 노리는 블로그 포스팅 초안을 마크다운으로 작성하세요.

키워드: {keyword}

반드시 지킬 형식:
# (클릭하고 싶어지는 제목. 키워드를 앞쪽에 포함, 40자 내외)

## 서론
(독자의 고민을 짚고 이 글에서 얻을 것을 안내. 첫 문단에 키워드 포함, 3~4문장)

## 본문
(소제목 ###을 3~5개 사용. 각 소제목마다 구체적인 설명, 예시, 목록(-)을 활용.
 키워드와 연관 키워드를 자연스럽게 반복하고, 전체 1,500자 이상)

## 결론
(핵심 요약 + 독자가 취할 다음 행동 제안)

## 해시태그
(#으로 시작하는 해시태그 7~10개를 한 줄에 공백으로 구분)

주의: 마크다운 본문만 출력하고, 코드블록(```)으로 감싸지 말며, 사실이 불확실한 수치나 통계는 지어내지 마세요."""


def slugify(keyword: str) -> str:
    """키워드를 파일명에 안전한 문자열로 바꾼다 (한글/영문/숫자만 남김)."""
    slug = re.sub(r"[^\w\s-]", "", keyword, flags=re.UNICODE).strip()
    return re.sub(r"[\s-]+", "_", slug) or "untitled"


def read_keywords() -> list[str]:
    if not KEYWORDS_FILE.exists():
        sys.exit("keywords.txt 파일이 없습니다.")
    lines = KEYWORDS_FILE.read_text(encoding="utf-8").splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")]


def already_done(keyword: str) -> bool:
    """날짜와 상관없이 같은 키워드의 글이 posts/에 있으면 처리 완료로 본다."""
    slug = slugify(keyword)
    return any(POSTS_DIR.glob(f"????-??-??_{slug}.md"))


def clean_output(text: str) -> str:
    """모델이 전체를 ```markdown 으로 감싼 경우 벗겨낸다."""
    text = text.strip()
    match = re.fullmatch(r"```(?:markdown|md)?\s*\n(.*?)\n```", text, flags=re.DOTALL)
    return (match.group(1) if match else text).strip()


def generate_post(model, keyword: str) -> str:
    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = model.generate_content(PROMPT_TEMPLATE.format(keyword=keyword))
            text = clean_output(response.text)
            if text:
                return text
            last_error = "빈 응답"
        except Exception as e:  # 네트워크/쿼터/안전필터 등
            last_error = e
        wait = DELAY_SECONDS * attempt * 2
        print(f"  ! 시도 {attempt}/{MAX_RETRIES} 실패: {last_error} → {wait}초 후 재시도")
        time.sleep(wait)
    raise RuntimeError(f"생성 실패: {last_error}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Gemini 블로그 글 자동 생성기")
    parser.add_argument("--limit", type=int, default=1,
                        help="이번 실행에서 만들 최대 글 수 (0 = 남은 키워드 전부, 기본 1)")
    args = parser.parse_args()

    load_dotenv(BASE_DIR / ".env")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        sys.exit("GEMINI_API_KEY가 없습니다. .env 파일 또는 GitHub Secrets를 확인하세요.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-2.0-flash"))

    POSTS_DIR.mkdir(exist_ok=True)
    keywords = read_keywords()
    todo = [k for k in keywords if not already_done(k)]
    print(f"전체 {len(keywords)}개 중 미처리 {len(todo)}개")
    if not todo:
        print("새로 만들 키워드가 없습니다. keywords.txt에 추가해 주세요.")
        return 0

    if args.limit > 0:
        todo = todo[: args.limit]

    created, failed = 0, 0
    for i, keyword in enumerate(todo):
        print(f"[{i + 1}/{len(todo)}] '{keyword}' 생성 중...")
        try:
            body = generate_post(model, keyword)
        except RuntimeError as e:
            print(f"  ✗ {e}")
            failed += 1
            continue
        path = POSTS_DIR / f"{date.today().isoformat()}_{slugify(keyword)}.md"
        path.write_text(body + "\n", encoding="utf-8")
        print(f"  ✓ 저장: {path.relative_to(BASE_DIR)}")
        created += 1
        if i < len(todo) - 1:
            time.sleep(DELAY_SECONDS)

    print(f"완료: 성공 {created}개, 실패 {failed}개")
    return 1 if failed and not created else 0


if __name__ == "__main__":
    sys.exit(main())
