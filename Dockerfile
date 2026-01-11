# 공모주 캘린더 봇 Docker 이미지
FROM python:3.11-slim

# 필수 시스템 패키지 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# 의존성 먼저 복사 (캐시 활용)
COPY requirements.txt .

# 의존성 설치
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY src/ src/
COPY docs/ docs/

# Git 설정 (커밋용)
RUN git config --global user.email "bot@gong-mo.calendar" \
    && git config --global user.name "Gong-mo Bot"

# 환경 변수 설정
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# 실행
CMD ["python", "-m", "gongmo.main", "--publish"]
