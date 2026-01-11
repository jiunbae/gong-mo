"""
IPO(공모주) 데이터 모델
"""

from datetime import date, datetime, timedelta
from enum import Enum
from typing import Optional
from dataclasses import dataclass, field
import hashlib


class IPOEventType(Enum):
    """공모주 이벤트 타입"""

    DEMAND_FORECAST = "demand_forecast"  # 수요예측
    SUBSCRIPTION = "subscription"  # 청약
    REFUND = "refund"  # 환불
    LISTING = "listing"  # 상장
    LOCKUP_EXPIRY = "lockup_expiry"  # 락업해제

    @property
    def korean_name(self) -> str:
        """한글 이름 반환"""
        names = {
            IPOEventType.DEMAND_FORECAST: "수요예측",
            IPOEventType.SUBSCRIPTION: "청약",
            IPOEventType.REFUND: "환불",
            IPOEventType.LISTING: "상장",
            IPOEventType.LOCKUP_EXPIRY: "락업해제",
        }
        return names[self]

    @property
    def color_id(self) -> str:
        """Google Calendar 색상 ID"""
        colors = {
            IPOEventType.DEMAND_FORECAST: "1",  # 라벤더
            IPOEventType.SUBSCRIPTION: "11",  # 토마토 (빨강)
            IPOEventType.REFUND: "5",  # 바나나 (노랑)
            IPOEventType.LISTING: "10",  # 바질 (녹색)
            IPOEventType.LOCKUP_EXPIRY: "6",  # 탠저린 (주황)
        }
        return colors[self]


@dataclass
class IPOSchedule:
    """공모주 일정 데이터 모델"""

    # 필수 필드
    company_name: str  # 회사명
    subscription_start: Optional[date] = None  # 청약 시작일
    subscription_end: Optional[date] = None  # 청약 종료일

    # 일정 관련
    demand_forecast_start: Optional[date] = None  # 수요예측 시작일
    demand_forecast_end: Optional[date] = None  # 수요예측 종료일
    refund_date: Optional[date] = None  # 환불일
    listing_date: Optional[date] = None  # 상장예정일
    lockup_expiry_date: Optional[date] = None  # 락업해제일

    # 공모 정보
    offer_price_min: Optional[int] = None  # 희망공모가 하단
    offer_price_max: Optional[int] = None  # 희망공모가 상단
    final_offer_price: Optional[int] = None  # 확정 공모가
    total_shares: Optional[int] = None  # 공모주식수
    total_amount: Optional[int] = None  # 공모금액 (억원)

    # 주관사 정보
    lead_underwriter: Optional[str] = None  # 대표주관사
    underwriters: list[str] = field(default_factory=list)  # 공동주관사

    # 청약 정보
    subscription_limit: Optional[int] = None  # 청약한도 (주)
    min_subscription: Optional[int] = None  # 최소청약주수
    deposit_rate: int = 50  # 청약증거금률 (%)

    # 경쟁률 정보
    institutional_competition: Optional[float] = None  # 기관 경쟁률
    retail_competition: Optional[float] = None  # 개인 경쟁률

    # 메타데이터
    stock_code: Optional[str] = None  # 종목코드 (상장 후)
    detail_url: Optional[str] = None  # 상세정보 URL
    source: str = "unknown"  # 데이터 소스
    collected_at: datetime = field(default_factory=datetime.now)  # 수집 시각

    @property
    def unique_id(self) -> str:
        """고유 ID 생성 (중복 방지용)"""
        raw = f"{self.company_name}_{self.subscription_start}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    @property
    def offer_price_range(self) -> str:
        """희망공모가 범위 문자열"""
        if self.final_offer_price:
            return f"{self.final_offer_price:,}원"
        if self.offer_price_min and self.offer_price_max:
            return f"{self.offer_price_min:,}~{self.offer_price_max:,}원"
        return "미정"

    @property
    def subscription_period(self) -> str:
        """청약 기간 문자열"""
        if self.subscription_start and self.subscription_end:
            start = self.subscription_start.strftime("%m/%d")
            end = self.subscription_end.strftime("%m/%d")
            return f"{start}~{end}"
        elif self.subscription_start:
            return self.subscription_start.strftime("%m/%d")
        return "미정"

    def get_calendar_events(self) -> list[dict]:
        """Google Calendar 이벤트 목록 생성"""
        events = []

        # 수요예측 이벤트
        if self.demand_forecast_start:
            events.append(
                self._create_event(
                    event_type=IPOEventType.DEMAND_FORECAST,
                    start_date=self.demand_forecast_start,
                    end_date=self.demand_forecast_end,
                )
            )

        # 청약 이벤트 (가장 중요)
        if self.subscription_start:
            events.append(
                self._create_event(
                    event_type=IPOEventType.SUBSCRIPTION,
                    start_date=self.subscription_start,
                    end_date=self.subscription_end,
                )
            )

        # 환불일 이벤트
        if self.refund_date:
            events.append(
                self._create_event(
                    event_type=IPOEventType.REFUND,
                    start_date=self.refund_date,
                )
            )

        # 상장일 이벤트
        if self.listing_date:
            events.append(
                self._create_event(
                    event_type=IPOEventType.LISTING,
                    start_date=self.listing_date,
                )
            )

        return events

    def _create_event(
        self,
        event_type: IPOEventType,
        start_date: date,
        end_date: Optional[date] = None,
    ) -> dict:
        """개별 캘린더 이벤트 생성"""
        # 이벤트 고유 ID
        event_unique_id = self._generate_event_id(event_type, start_date)

        # 제목 생성
        if event_type == IPOEventType.SUBSCRIPTION and end_date:
            title = f"[{event_type.korean_name}] {self.company_name} ({start_date.strftime('%m/%d')}-{end_date.strftime('%m/%d')})"
        else:
            title = f"[{event_type.korean_name}] {self.company_name}"

        # 설명 생성
        description = self._build_description(event_type)

        # 종료일 처리 (Google Calendar는 종일 이벤트의 end가 exclusive)
        actual_end = end_date or start_date
        end_date_exclusive = actual_end + timedelta(days=1)

        # 알림 설정
        reminders = self._get_reminders(event_type)

        return {
            "summary": title,
            "description": description,
            "start": {"date": start_date.isoformat()},
            "end": {"date": end_date_exclusive.isoformat()},
            "colorId": event_type.color_id,
            "reminders": reminders,
            "extendedProperties": {
                "private": {
                    "ipo_event_id": event_unique_id,
                    "company_name": self.company_name,
                    "event_type": event_type.value,
                    "source": "gong-mo-bot",
                }
            },
        }

    def _generate_event_id(self, event_type: IPOEventType, start_date: date) -> str:
        """이벤트별 고유 ID 생성"""
        raw = f"{self.company_name}_{event_type.value}_{start_date.isoformat()}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    def _build_description(self, event_type: IPOEventType) -> str:
        """이벤트 설명 생성"""
        lines = [
            f"[{event_type.korean_name}] {self.company_name}",
            "",
            "=== 공모 정보 ===",
            f"공모가: {self.offer_price_range}",
        ]

        if self.total_shares:
            lines.append(f"공모주식수: {self.total_shares:,}주")

        if self.total_amount:
            lines.append(f"공모금액: {self.total_amount:,}억원")

        lines.append("")
        lines.append("=== 주요 일정 ===")

        if self.demand_forecast_start:
            df_end = (
                f"~{self.demand_forecast_end}" if self.demand_forecast_end else ""
            )
            lines.append(f"수요예측: {self.demand_forecast_start}{df_end}")

        if self.subscription_start:
            sub_end = f"~{self.subscription_end}" if self.subscription_end else ""
            lines.append(f"청약: {self.subscription_start}{sub_end}")

        if self.refund_date:
            lines.append(f"환불: {self.refund_date}")

        if self.listing_date:
            lines.append(f"상장: {self.listing_date}")

        if self.lead_underwriter:
            lines.append("")
            lines.append("=== 주관사 ===")
            lines.append(f"대표주관: {self.lead_underwriter}")
            if self.underwriters:
                lines.append(f"공동주관: {', '.join(self.underwriters)}")

        if self.detail_url:
            lines.append("")
            lines.append(f"상세정보: {self.detail_url}")

        lines.append("")
        lines.append("---")
        lines.append("자동 생성: 공모주 캘린더 봇")

        return "\n".join(lines)

    def _get_reminders(self, event_type: IPOEventType) -> dict:
        """이벤트 타입별 알림 설정"""
        reminder_configs = {
            IPOEventType.DEMAND_FORECAST: [
                {"method": "popup", "minutes": 60 * 24},  # 1일 전
            ],
            IPOEventType.SUBSCRIPTION: [
                {"method": "popup", "minutes": 60 * 24 * 2},  # 2일 전
                {"method": "popup", "minutes": 60 * 24},  # 1일 전
                {"method": "popup", "minutes": 60 * 9},  # 당일 아침 (9시간 전)
            ],
            IPOEventType.REFUND: [
                {"method": "popup", "minutes": 60 * 9},  # 당일 아침
            ],
            IPOEventType.LISTING: [
                {"method": "popup", "minutes": 60 * 24},  # 1일 전
                {"method": "popup", "minutes": 60 * 9},  # 당일 아침
            ],
            IPOEventType.LOCKUP_EXPIRY: [
                {"method": "popup", "minutes": 60 * 24 * 7},  # 7일 전
                {"method": "popup", "minutes": 60 * 24},  # 1일 전
            ],
        }

        return {
            "useDefault": False,
            "overrides": reminder_configs.get(event_type, []),
        }

    def __str__(self) -> str:
        return f"IPO({self.company_name}, 청약: {self.subscription_period}, 공모가: {self.offer_price_range})"

    def __repr__(self) -> str:
        return self.__str__()
