"""
정적 사이트 데이터 생성기
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader

from .og_image import OGImageGenerator
from ..models.ipo import IPOSchedule
from ..config import settings

logger = logging.getLogger(__name__)


class StaticSiteGenerator:
    """정적 사이트용 데이터 및 HTML 생성"""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 템플릿 설정
        template_dir = Path(__file__).parent / "templates"
        self.jinja_env = Environment(loader=FileSystemLoader(template_dir))

    def generate(self, ipos: list[IPOSchedule]) -> Path:
        """IPO 데이터를 JSON 및 HTML 파일로 생성"""
        # 1. JSON 데이터 생성
        data = {
            "last_updated": datetime.now().isoformat(),
            "total_count": len(ipos),
            "items": [self._ipo_to_dict(ipo) for ipo in ipos],
        }

        json_path = self.output_dir / "data.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"정적 데이터 생성: {json_path} ({len(ipos)}건)")

        # 2. HTML 파일 생성 (SEO 최적화)
        self.generate_index(ipos)

        # 3. OG 이미지 생성
        try:
            og_gen = OGImageGenerator(self.output_dir)
            og_gen.generate(ipos)
        except Exception as e:
            logger.error(f"OG 이미지 생성 실패: {e}")

        return json_path

    def generate_index(self, ipos: list[IPOSchedule]):
        """SEO 메타 태그가 포함된 index.html 생성"""
        template = self.jinja_env.get_template("index.html.j2")

        # 다가오는 주요 IPO 요약 (메타 설명용)
        upcoming_ipos = [
            ipo
            for ipo in ipos
            if ipo.subscription_start
            and ipo.subscription_start >= datetime.now().date()
        ]
        upcoming_ipos.sort(key=lambda x: x.subscription_start or datetime.max.date())

        if upcoming_ipos:
            names = [ipo.company_name for ipo in upcoming_ipos[:3]]
            summary = f"[{', '.join(names)}] 등 {len(upcoming_ipos)}건의 청약 일정을 확인하세요."
            description = f"{datetime.now().month}월 공모주 일정: {summary} {settings.site_description}"
            title = f"{datetime.now().month}월 공모주 캘린더 - {upcoming_ipos[0].company_name} 외 {len(upcoming_ipos)}건"
        else:
            description = settings.site_description
            title = settings.site_title

        # 구조화 데이터 생성
        structured_data = [
            {
                "@context": "https://schema.org",
                "@type": "WebSite",
                "name": "공모주 캘린더",
                "description": description,
                "url": settings.site_url,
            }
        ]

        # 상위 5개 IPO 일정에 대해 Event 구조화 데이터 추가
        for ipo in upcoming_ipos[:5]:
            if ipo.subscription_start:
                event = {
                    "@context": "https://schema.org",
                    "@type": "Event",
                    "name": f"{ipo.company_name} 공모주 청약",
                    "description": f"{ipo.company_name} IPO 청약 일정. 공모가: {ipo.offer_price_range}",
                    "startDate": ipo.subscription_start.isoformat(),
                    "endDate": (
                        ipo.subscription_end or ipo.subscription_start
                    ).isoformat(),
                    "location": {
                        "@type": "Place",
                        "name": ipo.lead_underwriter or "증권사",
                        "address": "온라인 청약",
                    },
                    "eventStatus": "https://schema.org/EventScheduled",
                    "eventAttendanceMode": "https://schema.org/OnlineEventAttendanceMode",
                }
                structured_data.append(event)

        html_content = template.render(
            title=title,
            description=description,
            site_url=settings.site_url,
            og_image_url=f"{settings.site_url}og-image.png",
            structured_data=json.dumps(structured_data, ensure_ascii=False),
        )

        index_path = self.output_dir / "index.html"
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"인덱스 페이지 생성 완료: {index_path}")

    def _ipo_to_dict(self, ipo: IPOSchedule) -> dict:
        """IPOSchedule을 dict로 변환"""
        return {
            "company_name": ipo.company_name,
            "subscription_start": ipo.subscription_start.isoformat()
            if ipo.subscription_start
            else None,
            "subscription_end": ipo.subscription_end.isoformat()
            if ipo.subscription_end
            else None,
            "listing_date": ipo.listing_date.isoformat() if ipo.listing_date else None,
            "offer_price_range": ipo.offer_price_range,
            "final_offer_price": ipo.final_offer_price,
            "offer_price_min": ipo.offer_price_min,
            "offer_price_max": ipo.offer_price_max,
            "lead_underwriter": ipo.lead_underwriter,
            "institutional_competition": ipo.institutional_competition,
            "source": ipo.source,
            "detail_url": ipo.detail_url,
        }
