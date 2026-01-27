"""
OG 이미지 생성기 - Pillow 활용
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from ..models.ipo import IPOSchedule
from ..config import settings

logger = logging.getLogger(__name__)


class OGImageGenerator:
    """공모주 정보를 포함한 OG 이미지 생성"""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 폰트 설정 (Settings에서 로드)
        self.font_path = settings.font_path

        if not self.font_path or not Path(self.font_path).exists():
            self.font_path = None

    def generate(self, ipos: list[IPOSchedule], now: Optional[datetime] = None) -> Path:
        """수집된 데이터를 기반으로 OG 이미지 생성"""
        if now is None:
            now = datetime.now()

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
            title_font = self._get_font(
                60, index=1
            )  # TTC index 1이 대략 Bold인 경우 많음
            subtitle_font = self._get_font(40)
            list_font = self._get_font(35)
            footer_font = self._get_font(25)

            # 제목
            title = f"{now.year}년 {now.month}월 공모주 청약 일정"
            draw.text((60, 80), title, font=title_font, fill=(33, 37, 41))

            # 통계 정보
            stats_text = f"총 {len(ipos)}건의 일정"
            draw.text((60, 160), stats_text, font=subtitle_font, fill=(108, 117, 125))

            # 구분선
            draw.line([60, 220, 1140, 220], fill=(222, 226, 230), width=2)

            # 주요 일정 리스트 (최대 N개)
            y_offset = 260
            display_ipos = ipos[: settings.max_display_ipos]

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
                info = (
                    f"{ipo.lead_underwriter} | {price}"
                    if ipo.lead_underwriter
                    else price
                )
                draw.text((600, y_offset), info, font=list_font, fill=(108, 117, 125))

                y_offset += 60

            if len(ipos) > len(display_ipos):
                draw.text(
                    (80, y_offset + 10),
                    f"...외 {len(ipos) - len(display_ipos)}건 더보기",
                    font=subtitle_font,
                    fill=(0, 102, 204),
                )

            # 푸터
            footer_text = "jiun.dev/gong-mo | 공모주 캘린더 봇"
            draw.text((60, 560), footer_text, font=footer_font, fill=(173, 181, 189))

        except (AttributeError, TypeError, ValueError) as e:
            logger.error(f"OG 이미지 텍스트 그리기 실패: {e}")
            draw.text((60, 300), "공모주 캘린더", fill=(0, 0, 0))

        output_path = self.output_dir / "og-image.png"
        image.save(output_path, "PNG")

        # PWA 아이콘 생성 (효율성을 위해 별도 크기로 저장)
        for size in [192, 512]:
            icon_path = self.output_dir / f"icon-{size}.png"
            # 1:1 비율로 크롭하여 리사이즈
            icon_image = image.crop(
                (width // 2 - height // 2, 0, width // 2 + height // 2, height)
            )
            icon_image = icon_image.resize((size, size), Image.Resampling.LANCZOS)
            icon_image.save(icon_path, "PNG")
            logger.debug(f"PWA 아이콘 생성: {icon_path}")

        logger.info(f"OG 이미지 및 아이콘 생성 완료: {output_path}")
        return output_path

    def _get_font(self, size: int, index: int = 0) -> ImageFont.FreeTypeFont:
        """시스템 폰트 로드"""
        if self.font_path:
            try:
                return ImageFont.truetype(self.font_path, size, index=index)
            except (IOError, OSError):
                pass
        return ImageFont.load_default()
