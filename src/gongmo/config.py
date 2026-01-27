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
    google_calendar_id: str = "87a9feb0d01485564f1c4267d63b46ec329c3cb45c089f129a1c8edc546931cf@group.calendar.google.com"

    # Open DART API (선택사항)
    dart_api_key: str = ""

    # 크롤링 설정
    request_delay: float = 1.5  # 요청 간 대기 시간 (초)
    request_timeout: float = 10.0  # 요청 타임아웃 (초)
    max_retries: int = 3  # 최대 재시도 횟수

    # 로깅
    log_level: str = "INFO"

    site_url: str = "https://jiun.dev/gong-mo/"
    site_title: str = "공모주 캘린더 - 대한민국 IPO 청약 일정"
    site_description: str = "대한민국 공모주 청약 일정과 IPO 캘린더 정보를 확인하고, 구글 캘린더에 추가하여 놓치지 마세요."

    google_analytics_id: str = ""
    google_adsense_client_id: str = ""
    google_adsense_slot_top: str = ""
    google_adsense_slot_bottom: str = ""

    font_path: str = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
    max_display_ipos: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 전역 설정 인스턴스
settings = Settings()


def ensure_data_dir():
    """데이터 디렉토리 생성"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
