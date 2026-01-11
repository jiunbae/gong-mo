"""
정적 사이트 데이터 생성기
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..models.ipo import IPOSchedule

logger = logging.getLogger(__name__)


class StaticSiteGenerator:
    """정적 사이트용 데이터 생성"""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, ipos: list[IPOSchedule]) -> Path:
        """IPO 데이터를 JSON 파일로 생성"""
        data = {
            "last_updated": datetime.now().isoformat(),
            "total_count": len(ipos),
            "items": [self._ipo_to_dict(ipo) for ipo in ipos],
        }

        output_path = self.output_dir / "data.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"정적 데이터 생성: {output_path} ({len(ipos)}건)")
        return output_path

    def _ipo_to_dict(self, ipo: IPOSchedule) -> dict:
        """IPOSchedule을 dict로 변환"""
        return {
            "company_name": ipo.company_name,
            "subscription_start": ipo.subscription_start.isoformat() if ipo.subscription_start else None,
            "subscription_end": ipo.subscription_end.isoformat() if ipo.subscription_end else None,
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
