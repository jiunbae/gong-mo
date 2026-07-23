# 공모주 캘린더 봇

대한민국 공모주 청약 일정을 자동으로 수집하여 Google Calendar에 등록하고, 정적 웹사이트로 제공하는 봇입니다.

## Quickstart for Agents

<div><img src="https://quickstart-for-agents.vercel.app/api/header.svg?theme=claude-code&title=%EA%B3%B5%EB%AA%A8%EC%A3%BC%20%EC%BA%98%EB%A6%B0%EB%8D%94%20%EB%B4%87&lang=Agents&width=800&mascot=default&font=mono" width="100%" /></div>

```
Clone https://github.com/jiunbae/gong-mo and set up the project.
Install Python dependencies from requirements.txt.
Copy .env.example to .env and configure GOOGLE_CALENDAR_ID.
Run a dry-run with `PYTHONPATH=src python -m gongmo.main --dry-run`
to verify IPO data collection from 38커뮤니케이션.
Generate the static site with `PYTHONPATH=src python -m gongmo.main --publish`.
```

<div><img src="https://quickstart-for-agents.vercel.app/api/footer.svg?theme=claude-code&model=Opus%204.6&project=gong-mo&font=mono" width="100%" /></div>

## 기능

- 38커뮤니케이션에서 공모주 청약/상장 일정 자동 수집
- Google Calendar에 일정 자동 등록 (중복 방지)
- 정적 웹사이트 생성 및 GitHub Pages 배포
- Docker 지원

## 설치

```bash
# 저장소 클론
git clone https://github.com/jiunbae/gong-mo.git
cd gong-mo

# 가상환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

## Google Calendar API 설정

인증은 **서비스 계정(Service Account)** 방식만 사용합니다.

1. [Google Cloud Console](https://console.cloud.google.com)에서 프로젝트 생성
2. Calendar API 활성화
3. 서비스 계정 생성 후 JSON 키 발급
4. 자격 증명을 환경변수로 설정
   - CI/CD: `GOOGLE_SERVICE_ACCOUNT_KEY` = JSON 키 문자열
   - 로컬: `GOOGLE_SERVICE_ACCOUNT_FILE` = JSON 키 파일 경로
5. 대상 캘린더(`GOOGLE_CALENDAR_ID`)를 서비스 계정 이메일과 공유

## 사용법

```bash
# 공모주 수집 및 캘린더 등록
PYTHONPATH=src python -m gongmo.main

# 수집만 (캘린더 등록 안 함)
PYTHONPATH=src python -m gongmo.main --dry-run

# 등록된 일정 확인
PYTHONPATH=src python -m gongmo.main --list

# 정적 사이트 업데이트 및 GitHub 푸시
PYTHONPATH=src python -m gongmo.main --publish
```

## Docker

```bash
# 빌드 및 실행
docker-compose up gongmo-bot

# 캘린더 동기화만
docker-compose --profile sync up gongmo-sync

# Dry run
docker-compose --profile test up gongmo-dry
```

## 환경 변수

`.env` 파일에 설정:

```bash
GOOGLE_CALENDAR_ID=your_calendar_id@group.calendar.google.com
```

## 웹사이트

- URL: https://jiun.dev/gong-mo-calendar/
- 저장소: [jiunbae/gong-mo-calendar](https://github.com/jiunbae/gong-mo-calendar)

## 라이선스

MIT
