# auto-blog-generator

Gemini **무료 API**와 GitHub Actions로, 키워드만 적어 두면 **매일 블로그 글 초안(마크다운)을 자동으로 만들어 저장**해 주는 0원짜리 시스템입니다.

## 📁 파일 구조와 역할

| 파일/폴더 | 역할 |
|---|---|
| `generator.py` | 핵심 스크립트. 키워드를 읽어 Gemini로 글을 만들고 `posts/`에 저장 |
| `keywords.txt` | 글로 쓸 주제 목록 (한 줄에 하나) |
| `posts/` | 생성된 글이 `YYYY-MM-DD_키워드.md` 이름으로 저장되는 폴더 |
| `.env` / `.env.example` | 내 컴퓨터에서 쓰는 API 키 설정 (`.env`는 GitHub에 올라가지 않음) |
| `requirements.txt` | 필요한 파이썬 라이브러리 목록 |
| `.github/workflows/auto_post.yml` | 매일 자동 실행 + 결과 커밋 설정 |

## 🔑 1단계. Gemini API 키 발급 (무료)

1. <https://aistudio.google.com/apikey> 접속 → 구글 로그인
2. **Create API key** 클릭 → 생성된 키(`AIza...`)를 복사
3. 카드 등록은 필요 없습니다. 무료 사용량 제한(분당/일일 요청 수)이 있으며, 하루 1~수 개 글 생성에는 충분합니다.

## 💻 2단계. 내 컴퓨터에서 실행해 보기

```bash
# 1) 파이썬 3.9 이상 필요. 라이브러리 설치
pip install -r requirements.txt

# 2) API 키 설정
cp .env.example .env
#   → .env 파일을 열어 GEMINI_API_KEY= 뒤에 복사한 키를 붙여넣기

# 3) 실행
python generator.py              # 안 쓴 키워드 1개 처리
python generator.py --limit 3    # 최대 3개
python generator.py --limit 0    # 남은 키워드 전부
```

실행하면 `posts/2026-01-01_키워드.md` 같은 파일이 생깁니다. 마크다운 구성: **제목 → 서론 → 본문 → 결론 → 해시태그**.

### 중복 방지는 어떻게 되나요?
`posts/`에 같은 키워드의 글이 (날짜와 무관하게) 이미 있으면 **자동으로 건너뛰고 다음 키워드**로 넘어갑니다. 글을 다시 만들고 싶다면 해당 `.md` 파일을 삭제하세요.

## ☁️ 3단계. GitHub Actions로 매일 자동 실행

1. 이 폴더를 GitHub 저장소에 올립니다.
2. 저장소 **Settings → Secrets and variables → Actions → New repository secret**
   - Name: `GEMINI_API_KEY`
   - Secret: 발급받은 API 키
3. **Settings → Actions → General → Workflow permissions**에서 **Read and write permissions** 선택 후 Save (글을 자동 커밋하기 위해 필요)
4. **Actions 탭 → Auto Blog Post → Run workflow**로 먼저 수동 테스트
5. 이후 매일 자동 실행됩니다. 새 글은 `posts/`에 자동 커밋됩니다.

### 실행 시간 바꾸기
`.github/workflows/auto_post.yml`의 `cron: "0 0 * * *"` 은 **UTC 기준**입니다. 한국시간(KST)은 UTC+9이므로:

| 원하는 한국 시간 | cron |
|---|---|
| 오전 9시 | `0 0 * * *` (기본값) |
| 오후 6시 | `0 9 * * *` |
| 평일 오전 7시 | `0 22 * * 0-4` |

> GitHub 스케줄은 몇 분~수십 분 늦게 실행될 수 있고, 저장소에 60일간 활동이 없으면 스케줄이 자동 중지됩니다(자동 커밋이 있으면 계속 유지).
> 하루에 만들 글 수를 늘리려면 워크플로의 `--limit 1`을 바꾸세요.

## ❓ 문제 해결

- **`GEMINI_API_KEY가 없습니다`** → `.env` 파일(로컬) 또는 GitHub Secret(자동화) 이름/값 확인
- **429 / quota 오류** → 무료 한도 초과. 잠시 후 재실행하거나 `--limit`을 줄이세요.
- **모델을 바꾸고 싶다면** → `.env`에 `GEMINI_MODEL=모델이름` 추가
- **참고**: `google-generativeai` 라이브러리는 구글이 지원 종료를 안내했습니다. 현재 동작에는 문제가 없으나, 오류가 계속되면 후속 라이브러리 `google-genai`로 옮기는 것을 권장합니다.

## ⚠️ 사용 팁
생성된 글은 **초안**입니다. 사실관계를 확인하고 본인 경험을 더해 발행하세요. API 키는 절대 코드나 `.env.example`에 직접 적지 마세요.
