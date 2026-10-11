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

---

# 📣 Blogger 자동 게시 설정 (구글 블로그)

`posts/`에 새 글이 push되면 `.github/workflows/publish_blogger.yml`이 `publish_blogger.py`를 실행해 Blogger에 자동으로 올립니다. 올린 글은 `published.json`에 기록되어 중복 게시되지 않습니다. (매일 09:30 KST에도 한 번 확인합니다.)

## 주제는 매주 바뀝니다
`weekly_theme.txt`에 이번 주 테마가 적혀 있고, 매주 월요일에 새 테마로 바뀝니다. 그 주의 글은 모두 그 테마 안에서 서로 겹치지 않는 키워드로 작성됩니다.

## 1단계. Blogger 블로그 만들기
1. <https://www.blogger.com> 에서 블로그를 만듭니다.
2. 블로그 ID 확인: 블로그 관리 화면 주소 `blogger.com/blog/posts/숫자` 의 **숫자**가 Blog ID입니다.

## 2단계. 구글 API 인증 정보 만들기 (한 번만)
1. <https://console.cloud.google.com> → 새 프로젝트 생성
2. **API 및 서비스 → 라이브러리**에서 **Blogger API v3**를 검색해 **사용**
3. **OAuth 동의 화면** 설정: 사용자 유형 **외부**, 앱 이름과 본인 이메일만 입력
4. ⚠️ **게시 상태를 반드시 "프로덕션으로 푸시"** 하세요. "테스트" 상태에서는 리프레시 토큰이 **7일 만에 만료**되어 자동 게시가 멈춥니다. (본인만 쓰는 앱은 구글 검증 없이 프로덕션으로 둘 수 있고, 로그인 때 "확인되지 않은 앱" 경고가 뜨는 것은 정상입니다.)
5. **사용자 인증 정보 → 사용자 인증 정보 만들기 → OAuth 클라이언트 ID** → 유형 **웹 애플리케이션**, **승인된 리디렉션 URI**에 `https://developers.google.com/oauthplayground` 추가 → **클라이언트 ID**와 **클라이언트 보안 비밀번호** 복사

## 3단계. 리프레시 토큰 받기
1. <https://developers.google.com/oauthplayground> 접속
2. 오른쪽 위 톱니바퀴 ⚙ → **Use your own OAuth credentials** 체크 → 위에서 복사한 클라이언트 ID/보안 비밀번호 입력
3. 왼쪽 입력칸에 `https://www.googleapis.com/auth/blogger` 입력 → **Authorize APIs** → 블로그 주인 계정으로 로그인, 허용
4. **Exchange authorization code for tokens** 클릭 → **Refresh token** 복사

## 4단계. GitHub Secrets 등록
저장소 **Settings → Secrets and variables → Actions → New repository secret** 에서 4개를 등록합니다.

| Name | 값 |
|---|---|
| `BLOGGER_BLOG_ID` | 1단계의 Blog ID |
| `GOOGLE_CLIENT_ID` | 2단계의 클라이언트 ID |
| `GOOGLE_CLIENT_SECRET` | 2단계의 보안 비밀번호 |
| `GOOGLE_REFRESH_TOKEN` | 3단계의 Refresh token |

## 5단계. 테스트
**Actions → Publish to Blogger → Run workflow**. 성공하면 Blogger에 글이 올라가고 `published.json`에 주소가 기록됩니다. 로컬에서 대상만 확인하려면 `python publish_blogger.py --dry-run`.

## 문제 해결
- **리프레시 토큰이 7일 만에 만료될 때** (`invalid_grant`): OAuth 동의 화면이 "테스트" 상태입니다. "프로덕션"으로 바꾼 뒤 3단계로 토큰을 다시 받아 Secret을 교체하세요.
- **403 / 권한 오류**: 로그인한 구글 계정이 그 블로그의 주인(또는 작성자)인지, Blogger API가 켜져 있는지 확인하세요.
- **같은 글이 두 번 올라갔을 때**: Blogger 관리 화면에서 삭제하고 `published.json`에 기록이 있는지 확인하세요.

> 💡 광고(애드센스)는 Blogger 관리 화면의 **수익 창출**에서 연결합니다. 승인 심사에는 글의 품질과 양이 중요하니, AI 초안은 출처와 본인 경험을 보태 다듬어 올리는 것을 권장합니다.
