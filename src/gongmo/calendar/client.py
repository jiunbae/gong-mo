"""
Google Calendar API 클라이언트
"""

import logging
from enum import Enum
from typing import Optional
from dataclasses import dataclass

from googleapiclient.errors import HttpError
from googleapiclient.discovery import Resource

from .auth import get_calendar_service
from ..models.ipo import IPOSchedule
from ..config import settings

logger = logging.getLogger(__name__)


class SyncAction(Enum):
    """동기화 액션 타입"""

    CREATE = "create"
    UPDATE = "update"
    SKIP = "skip"
    DELETE = "delete"
    ERROR = "error"


@dataclass
class SyncResult:
    """동기화 결과"""

    action: SyncAction
    event_title: str
    event_id: Optional[str] = None
    event_link: Optional[str] = None
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.action != SyncAction.ERROR


class GoogleCalendarClient:
    """Google Calendar API 클라이언트"""

    def __init__(
        self,
        calendar_id: str = None,
        service: Resource = None,
    ):
        self.calendar_id = calendar_id or settings.google_calendar_id
        self._service = service

    @property
    def service(self) -> Resource:
        """서비스 객체 (lazy loading)"""
        if self._service is None:
            self._service = get_calendar_service()
        return self._service

    def sync_ipo(self, ipo: IPOSchedule) -> list[SyncResult]:
        """IPO 일정 동기화 (생성/수정/스킵)"""
        results = []

        # IPO에서 캘린더 이벤트 목록 생성
        events = ipo.get_calendar_events()

        for event_body in events:
            result = self._sync_single_event(event_body)
            results.append(result)

        return results

    def _sync_single_event(self, event_body: dict) -> SyncResult:
        """단일 이벤트 동기화"""
        event_title = event_body.get("summary", "Unknown")
        event_id = event_body.get("extendedProperties", {}).get("private", {}).get("ipo_event_id")

        try:
            # 기존 이벤트 검색
            existing = self._find_existing_event(event_id)

            if existing is None:
                # 새 이벤트 생성
                created = self.service.events().insert(
                    calendarId=self.calendar_id,
                    body=event_body,
                ).execute()

                logger.info(f"이벤트 생성: {event_title}")
                return SyncResult(
                    action=SyncAction.CREATE,
                    event_title=event_title,
                    event_id=created.get("id"),
                    event_link=created.get("htmlLink"),
                )

            elif self._should_update(existing, event_body):
                # 기존 이벤트 수정
                updated = self.service.events().update(
                    calendarId=self.calendar_id,
                    eventId=existing["id"],
                    body=event_body,
                ).execute()

                logger.info(f"이벤트 수정: {event_title}")
                return SyncResult(
                    action=SyncAction.UPDATE,
                    event_title=event_title,
                    event_id=updated.get("id"),
                    event_link=updated.get("htmlLink"),
                )

            else:
                # 변경 없음
                logger.debug(f"이벤트 스킵 (변경 없음): {event_title}")
                return SyncResult(
                    action=SyncAction.SKIP,
                    event_title=event_title,
                    event_id=existing.get("id"),
                    event_link=existing.get("htmlLink"),
                )

        except HttpError as e:
            logger.error(f"이벤트 동기화 실패 ({event_title}): {e}")
            return SyncResult(
                action=SyncAction.ERROR,
                event_title=event_title,
                error=str(e),
            )

    def _find_existing_event(self, ipo_event_id: str) -> Optional[dict]:
        """extendedProperties로 기존 이벤트 검색"""
        if not ipo_event_id:
            return None

        try:
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                privateExtendedProperty=f"ipo_event_id={ipo_event_id}",
                singleEvents=True,
                maxResults=1,
            ).execute()

            events = events_result.get("items", [])
            return events[0] if events else None

        except HttpError as e:
            logger.warning(f"이벤트 검색 실패: {e}")
            return None

    def _should_update(self, existing: dict, new_body: dict) -> bool:
        """업데이트 필요 여부 확인"""
        # 주요 필드 비교
        if existing.get("summary") != new_body.get("summary"):
            return True
        if existing.get("start") != new_body.get("start"):
            return True
        if existing.get("end") != new_body.get("end"):
            return True

        # 설명은 길이 변화가 있을 때만 업데이트
        existing_desc = existing.get("description", "")
        new_desc = new_body.get("description", "")
        if len(existing_desc) != len(new_desc):
            return True

        return False

    def delete_ipo_events(self, ipo: IPOSchedule) -> list[SyncResult]:
        """IPO 관련 모든 이벤트 삭제"""
        results = []

        try:
            # 회사명으로 이벤트 검색 (source 필터는 결과에서 확인)
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                privateExtendedProperty=f"company_name={ipo.company_name}",
                singleEvents=True,
            ).execute()

            events = events_result.get("items", [])

            for event in events:
                try:
                    self.service.events().delete(
                        calendarId=self.calendar_id,
                        eventId=event["id"],
                    ).execute()

                    results.append(SyncResult(
                        action=SyncAction.DELETE,
                        event_title=event.get("summary", "Unknown"),
                        event_id=event["id"],
                    ))
                    logger.info(f"이벤트 삭제: {event.get('summary')}")

                except HttpError as e:
                    results.append(SyncResult(
                        action=SyncAction.ERROR,
                        event_title=event.get("summary", "Unknown"),
                        event_id=event["id"],
                        error=str(e),
                    ))

        except HttpError as e:
            logger.error(f"이벤트 검색 실패: {e}")

        return results

    def list_upcoming_events(self, max_results: int = 10) -> list[dict]:
        """다가오는 이벤트 목록 조회"""
        try:
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc).isoformat()

            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
                privateExtendedProperty="source=gong-mo-bot",
            ).execute()

            return events_result.get("items", [])

        except HttpError as e:
            logger.error(f"이벤트 조회 실패: {e}")
            return []

    def get_calendar_info(self) -> Optional[dict]:
        """캘린더 정보 조회"""
        try:
            calendar = self.service.calendars().get(
                calendarId=self.calendar_id
            ).execute()
            return calendar
        except HttpError as e:
            logger.error(f"캘린더 정보 조회 실패: {e}")
            return None

    def cleanup_all_events(self) -> list[SyncResult]:
        """gong-mo-bot이 생성한 모든 이벤트 삭제 (전체 초기화용)"""
        results = []

        try:
            # source=gong-mo-bot인 모든 이벤트 검색
            page_token = None
            all_events = []

            while True:
                events_result = self.service.events().list(
                    calendarId=self.calendar_id,
                    privateExtendedProperty="source=gong-mo-bot",
                    singleEvents=True,
                    maxResults=250,
                    pageToken=page_token,
                ).execute()

                all_events.extend(events_result.get("items", []))
                page_token = events_result.get("nextPageToken")

                if not page_token:
                    break

            logger.info(f"삭제할 이벤트 {len(all_events)}개 발견")

            for event in all_events:
                try:
                    self.service.events().delete(
                        calendarId=self.calendar_id,
                        eventId=event["id"],
                    ).execute()

                    results.append(SyncResult(
                        action=SyncAction.DELETE,
                        event_title=event.get("summary", "Unknown"),
                        event_id=event["id"],
                    ))
                    logger.info(f"이벤트 삭제: {event.get('summary')}")

                except HttpError as e:
                    results.append(SyncResult(
                        action=SyncAction.ERROR,
                        event_title=event.get("summary", "Unknown"),
                        event_id=event["id"],
                        error=str(e),
                    ))

        except HttpError as e:
            logger.error(f"이벤트 검색 실패: {e}")

        return results

    def cleanup_company_events(self, company_name: str) -> list[SyncResult]:
        """특정 회사의 모든 이벤트 삭제 (중복 정리용)"""
        results = []

        try:
            # 회사명으로 이벤트 검색
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                privateExtendedProperty=f"company_name={company_name}",
                singleEvents=True,
                maxResults=50,
            ).execute()

            events = events_result.get("items", [])
            logger.info(f"{company_name}: {len(events)}개 이벤트 발견")

            for event in events:
                try:
                    self.service.events().delete(
                        calendarId=self.calendar_id,
                        eventId=event["id"],
                    ).execute()

                    results.append(SyncResult(
                        action=SyncAction.DELETE,
                        event_title=event.get("summary", "Unknown"),
                        event_id=event["id"],
                    ))
                    logger.info(f"이벤트 삭제: {event.get('summary')}")

                except HttpError as e:
                    results.append(SyncResult(
                        action=SyncAction.ERROR,
                        event_title=event.get("summary", "Unknown"),
                        event_id=event["id"],
                        error=str(e),
                    ))

        except HttpError as e:
            logger.error(f"이벤트 검색 실패: {e}")

        return results
