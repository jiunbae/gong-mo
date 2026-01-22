"""
설정 관리 모듈
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 기본 경로 설정
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
CREDENTIALS_PATH = BASE_DIR / "credentials.json"
TOKEN_PATH = BASE_DIR / "token.json"


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # Google Calendar
    google_calendar_id: str = "REDACTED_CALENDAR_ID@group.calendar.google.com"

    # Open DART API (선택사항)
    dart_api_key: str = ""

    # 크롤링 설정
    request_delay: float = 1.5  # 요청 간 대기 시간 (초)
    request_timeout: float = 10.0  # 요청 타임아웃 (초)
    max_retries: int = 3  # 최대 재시도 횟수

    # 로깅
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 전역 설정 인스턴스
settings = Settings()


def ensure_data_dir():
    """데이터 디렉토리 생성"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
