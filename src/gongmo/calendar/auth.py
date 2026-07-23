"""
Google Calendar API 인증 모듈

인증 방식: Service Account
  - GOOGLE_SERVICE_ACCOUNT_KEY 환경변수: JSON 키 문자열 (CI/CD 권장)
  - GOOGLE_SERVICE_ACCOUNT_FILE 환경변수: JSON 키 파일 경로 (로컬)
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build, Resource

logger = logging.getLogger(__name__)

# Google Calendar API 권한 범위
SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_service_account_credentials() -> Optional[service_account.Credentials]:
    """
    환경 변수에서 Service Account 자격 증명을 로드합니다.

    Returns:
        Service Account 자격 증명 또는 None (환경 변수가 없는 경우)
    """
    # 방법 1: JSON 문자열로 전달
    sa_key = os.environ.get("GOOGLE_SERVICE_ACCOUNT_KEY")
    if sa_key:
        try:
            key_data = json.loads(sa_key)
            creds = service_account.Credentials.from_service_account_info(
                key_data, scopes=SCOPES
            )
            logger.info("Service Account 인증 성공 (환경 변수)")
            return creds
        except json.JSONDecodeError as e:
            logger.error(f"GOOGLE_SERVICE_ACCOUNT_KEY JSON 파싱 실패: {e}")
        except Exception as e:
            logger.error(f"Service Account 인증 실패: {e}")

    # 방법 2: 파일 경로로 전달
    sa_file = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")
    if sa_file and Path(sa_file).exists():
        try:
            creds = service_account.Credentials.from_service_account_file(
                sa_file, scopes=SCOPES
            )
            logger.info(f"Service Account 인증 성공 (파일: {sa_file})")
            return creds
        except Exception as e:
            logger.error(f"Service Account 파일 인증 실패: {e}")

    return None


# 싱글톤 서비스 인스턴스
_calendar_service: Optional[Resource] = None

# 서비스 계정 미설정 시 안내 메시지
_MISSING_SA_MESSAGE = (
    "Google Calendar 인증에 필요한 Service Account 자격 증명을 찾을 수 없습니다.\n"
    "다음 중 하나를 설정하세요:\n"
    "  - GOOGLE_SERVICE_ACCOUNT_KEY: 서비스 계정 JSON 키 문자열 (CI/CD 권장)\n"
    "  - GOOGLE_SERVICE_ACCOUNT_FILE: 서비스 계정 JSON 키 파일 경로 (로컬)\n"
    "설정 방법: Google Cloud Console에서 서비스 계정을 만들고 JSON 키를 발급받은 뒤,\n"
    "대상 캘린더를 해당 서비스 계정 이메일과 공유하세요."
)


class GoogleCalendarAuth:
    """Google Calendar 인증 관리 클래스 (Service Account 전용)"""

    def __init__(self):
        self._service: Optional[Resource] = None

    def authenticate(self) -> service_account.Credentials:
        """
        Service Account 자격 증명을 반환합니다.

        Raises:
            FileNotFoundError: 서비스 계정 자격 증명이 설정되지 않은 경우
        """
        creds = get_service_account_credentials()
        if creds is None:
            raise FileNotFoundError(_MISSING_SA_MESSAGE)
        return creds

    def get_service(self) -> Resource:
        """Google Calendar API 서비스 객체 반환"""
        if self._service is None:
            creds = self.authenticate()
            self._service = build("calendar", "v3", credentials=creds)
            logger.info("Google Calendar 서비스 초기화 완료")
        return self._service

    def is_authenticated(self) -> bool:
        """인증 상태 확인 (서비스 계정 설정 여부)"""
        return get_service_account_credentials() is not None


def get_calendar_service() -> Resource:
    """Calendar API 서비스 인스턴스 반환 (싱글톤)"""
    global _calendar_service

    if _calendar_service is None:
        auth = GoogleCalendarAuth()
        _calendar_service = auth.get_service()

    return _calendar_service


def reset_calendar_service() -> None:
    """서비스 인스턴스 리셋 (테스트용)"""
    global _calendar_service
    _calendar_service = None
