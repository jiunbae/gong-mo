"""
크롤러 테스트
"""

import pytest
from datetime import date

import sys
sys.path.insert(0, "src")

from gongmo.collectors.site38 import Site38Collector
from gongmo.models.ipo import IPOSchedule, IPOEventType


class TestSite38Collector:
    """38커뮤니케이션 크롤러 테스트"""

    def test_collect_returns_list(self):
        """수집 결과가 리스트인지 확인"""
        collector = Site38Collector()
        result = collector.collect()
        assert isinstance(result, list)

    def test_collect_returns_ipo_schedules(self):
        """수집 결과가 IPOSchedule 객체인지 확인"""
        collector = Site38Collector()
        result = collector.collect()
        if result:
            assert isinstance(result[0], IPOSchedule)

    def test_collected_data_has_company_name(self):
        """수집된 데이터에 회사명이 있는지 확인"""
        collector = Site38Collector()
        result = collector.collect()
        if result:
            for ipo in result:
                assert ipo.company_name
                assert len(ipo.company_name) > 0

    def test_collected_data_has_subscription_date(self):
        """수집된 데이터에 청약일이 있는지 확인"""
        collector = Site38Collector()
        result = collector.collect()
        if result:
            for ipo in result:
                assert ipo.subscription_start is not None


class TestIPOSchedule:
    """IPO 데이터 모델 테스트"""

    def test_unique_id_generation(self):
        """고유 ID 생성 테스트"""
        ipo = IPOSchedule(
            company_name="테스트기업",
            subscription_start=date(2025, 1, 15),
            subscription_end=date(2025, 1, 16),
        )
        assert ipo.unique_id
        assert len(ipo.unique_id) == 16

    def test_offer_price_range_with_final(self):
        """확정 공모가 표시 테스트"""
        ipo = IPOSchedule(
            company_name="테스트",
            final_offer_price=10000,
        )
        assert ipo.offer_price_range == "10,000원"

    def test_offer_price_range_with_range(self):
        """희망 공모가 범위 표시 테스트"""
        ipo = IPOSchedule(
            company_name="테스트",
            offer_price_min=10000,
            offer_price_max=12000,
        )
        assert ipo.offer_price_range == "10,000~12,000원"

    def test_calendar_events_generation(self):
        """캘린더 이벤트 생성 테스트"""
        ipo = IPOSchedule(
            company_name="테스트기업",
            subscription_start=date(2025, 1, 15),
            subscription_end=date(2025, 1, 16),
            listing_date=date(2025, 1, 25),
        )
        events = ipo.get_calendar_events()
        assert len(events) == 2  # 청약 + 상장

    def test_event_has_required_fields(self):
        """이벤트에 필수 필드가 있는지 확인"""
        ipo = IPOSchedule(
            company_name="테스트기업",
            subscription_start=date(2025, 1, 15),
            subscription_end=date(2025, 1, 16),
        )
        events = ipo.get_calendar_events()
        event = events[0]

        assert "summary" in event
        assert "start" in event
        assert "end" in event
        assert "colorId" in event
        assert "reminders" in event
        assert "extendedProperties" in event


class TestIPOEventType:
    """이벤트 타입 테스트"""

    def test_korean_name(self):
        """한글 이름 테스트"""
        assert IPOEventType.SUBSCRIPTION.korean_name == "청약"
        assert IPOEventType.LISTING.korean_name == "상장"

    def test_color_id(self):
        """색상 ID 테스트"""
        assert IPOEventType.SUBSCRIPTION.color_id == "11"  # 빨강
        assert IPOEventType.LISTING.color_id == "10"  # 녹색
