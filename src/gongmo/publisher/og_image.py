"""
OG 이미지 생성기 - Pillow 활용
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from ..models.ipo import IPOSchedule

logger = logging.getLogger(__name__)


class OGImageGenerator:
    """공모주 정보를 포함한 OG 이미지 생성"""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 폰트 설정 (macOS 기준)
        self.font_path = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
        if not Path(self.font_path).exists():
            # 시스템 폰트가 없을 경우 기본 폰트 사용
            self.font_path = None

    def generate(self, ipos: list[IPOSchedule]) -> Path:
        """수집된 데이터를 기반으로 OG 이미지 생성"""
        # 이미지 크기 (OG 규격: 1200x630)
        width, height = 1200, 630

        # 배경색 (공모주 느낌의 파란색 톤)
        background_color = (255, 255, 255)
        image = Image.new("RGB", (width, height), background_color)
        draw = ImageDraw.Draw(image)

        # 장식 요소 (상단 바)
        draw.rectangle([0, 0, width, 20], fill=(0, 102, 204))

        # 텍스트 로직
        try:
            # 폰트 로드
            title_font = self._get_font(60, bold=True)
            subtitle_font = self._get_font(40)
            list_font = self._get_font(35)
            footer_font = self._get_font(25)

            # 제목
            now = datetime.now()
            title = f"{now.year}년 {now.month}월 공모주 청약 일정"
            draw.text((60, 80), title, font=title_font, fill=(33, 37, 41))

            # 통계 정보
            upcoming_ipos = [
                ipo
                for ipo in ipos
                if ipo.subscription_start and ipo.subscription_start >= now.date()
            ]
            stats_text = f"총 {len(ipos)}건의 일정 | 청약 예정 {len(upcoming_ipos)}건"
            draw.text((60, 160), stats_text, font=subtitle_font, fill=(108, 117, 125))

            # 구분선
            draw.line([60, 220, 1140, 220], fill=(222, 226, 230), width=2)

            # 주요 일정 리스트 (최대 5개)
            y_offset = 260
            display_ipos = upcoming_ipos[:5] if upcoming_ipos else ipos[:5]

            for ipo in display_ipos:
                date_str = (
                    ipo.subscription_start.strftime("%m/%d")
                    if ipo.subscription_start
                    else "미정"
                )
                text = f"• [{date_str}] {ipo.company_name}"
                draw.text((80, y_offset), text, font=list_font, fill=(52, 58, 64))

                # 주관사/공모가 요약 (우측)
                price = ipo.offer_price_range
                info = f"{ipo.lead_underwriter or ''} | {price}"
                draw.text((600, y_offset), info, font=list_font, fill=(108, 117, 125))

                y_offset += 60

            if len(display_ipos) < len(upcoming_ipos):
                draw.text(
                    (80, y_offset + 10),
                    f"...외 {len(upcoming_ipos) - len(display_ipos)}건 더보기",
                    font=subtitle_font,
                    fill=(0, 102, 204),
                )

            # 푸터
            footer_text = "jiun.dev/gong-mo | 공모주 캘린더 봇"
            draw.text((60, 560), footer_text, font=footer_font, fill=(173, 181, 189))

        except Exception as e:
            logger.error(f"OG 이미지 텍스트 그리기 실패: {e}")
            # 최소한의 텍스트라도 출력
            draw.text((60, 300), "공모주 캘린더", fill=(0, 0, 0))

        output_path = self.output_dir / "og-image.png"
        image.save(output_path, "PNG")

        logger.info(f"OG 이미지 생성 완료: {output_path}")
        return output_path

    def _get_font(self, size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
        """시스템 폰트 로드"""
        if self.font_path:
            try:
                # TTC 파일의 경우 인덱스 지정이 필요할 수 있음
                return ImageFont.truetype(self.font_path, size, index=0)
            except Exception:
                return ImageFont.load_default()
        return ImageFont.load_default()
