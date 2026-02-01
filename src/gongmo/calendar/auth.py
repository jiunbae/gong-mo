"""
Google Calendar API 인증 모듈

지원하는 인증 방식:
1. Service Account (CI/CD 환경 권장)
   - GOOGLE_SERVICE_ACCOUNT_KEY 환경변수: JSON 키 문자열
   - GOOGLE_SERVICE_ACCOUNT_FILE 환경변수: JSON 키 파일 경로

2. OAuth 2.0 (로컬 개발용)
   - credentials.json + token.json 파일 사용
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource

from ..config import CREDENTIALS_PATH, TOKEN_PATH

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


class GoogleCalendarAuth:
    """Google Calendar 인증 관리 클래스"""

    def __init__(
        self,
        credentials_path: Path = CREDENTIALS_PATH,
        token_path: Path = TOKEN_PATH,
    ):
        self.credentials_path = Path(credentials_path)
        self.token_path = Path(token_path)
        self._service: Optional[Resource] = None

    def authenticate(self) -> Credentials:
        """
        인증 수행 및 자격 증명 반환

        우선순위:
        1. Service Account (환경 변수)
        2. OAuth 토큰 파일 (token.json)
        3. 새 OAuth 인증 (credentials.json 필요)
        """
        # Service Account 우선 확인 (CI/CD 환경)
        sa_creds = get_service_account_credentials()
        if sa_creds:
            return sa_creds

        creds = None

        # 기존 토큰 확인
        if self.token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(
                    str(self.token_path), SCOPES
                )
                logger.debug("기존 토큰 로드 성공")
            except Exception as e:
                logger.warning(f"토큰 로드 실패: {e}")
                creds = None

        # 유효하지 않은 경우 갱신 또는 새로 인증
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # 토큰 갱신
                try:
                    creds.refresh(Request())
                    logger.info("토큰 갱신 성공")
                except Exception as e:
                    logger.warning(f"토큰 갱신 실패, 재인증 필요: {e}")
                    creds = None

            if not creds:
                # 새로운 인증 플로우 시작
                if not self.credentials_path.exists():
                    raise FileNotFoundError(
                        f"credentials.json 파일을 찾을 수 없습니다: {self.credentials_path}\n"
                        "Google Cloud Console에서 OAuth 자격 증명을 다운로드하세요.\n"
                        "설정 방법: https://developers.google.com/calendar/api/quickstart/python"
                    )

                logger.info("새로운 인증 시작...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), SCOPES
                )
                creds = flow.run_local_server(
                    port=54321,
                    prompt="consent",
                    success_message="인증 성공! 이 창을 닫아도 됩니다.",
                    open_browser=True,
                )
                logger.info("새 인증 완료")

            # 토큰 저장
            self._save_token(creds)

        return creds

    def _save_token(self, creds: Credentials) -> None:
        """토큰을 파일에 저장"""
        try:
            # 상위 디렉토리 생성
            self.token_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.token_path, "w") as token:
                token.write(creds.to_json())
            logger.debug(f"토큰 저장됨: {self.token_path}")
        except Exception as e:
            logger.error(f"토큰 저장 실패: {e}")

    def get_service(self) -> Resource:
        """Google Calendar API 서비스 객체 반환"""
        if self._service is None:
            creds = self.authenticate()
            self._service = build("calendar", "v3", credentials=creds)
            logger.info("Google Calendar 서비스 초기화 완료")
        return self._service

    def revoke_token(self) -> bool:
        """토큰 취소 (로그아웃)"""
        if self.token_path.exists():
            self.token_path.unlink()
            self._service = None
            logger.info("토큰 삭제됨")
            return True
        return False

    def is_authenticated(self) -> bool:
        """인증 상태 확인"""
        # Service Account가 설정되어 있으면 True
        if get_service_account_credentials():
            return True

        if not self.token_path.exists():
            return False

        try:
            creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
            return creds.valid or (creds.expired and creds.refresh_token)
        except Exception:
            return False


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
