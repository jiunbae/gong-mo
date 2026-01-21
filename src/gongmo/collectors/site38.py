"""
38커뮤니케이션 크롤러
http://www.38.co.kr/html/fund/
"""

import re
import time
from datetime import datetime, date
from typing import Optional
import logging

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from .base import BaseCollector
from ..models.ipo import IPOSchedule
from ..config import settings

logger = logging.getLogger(__name__)


class Site38Collector(BaseCollector):
    """38커뮤니케이션 공모주 정보 수집기"""

    source_name = "38커뮤니케이션"
    BASE_URL = "http://www.38.co.kr"
    IPO_LIST_URL = f"{BASE_URL}/html/fund/index.htm"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    }

    def __init__(self):
        self.client = httpx.Client(
            headers=self.HEADERS,
            timeout=settings.request_timeout,
            follow_redirects=True,
        )

    def __del__(self):
        if hasattr(self, "client"):
            self.client.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def _fetch_page(self, url: str) -> str:
        """페이지 HTML 가져오기"""
        response = self.client.get(url)
        response.raise_for_status()
        # 38커뮤니케이션은 EUC-KR 인코딩 사용
        response.encoding = "euc-kr"
        return response.text

    def collect(self) -> list[IPOSchedule]:
        """공모주 청약 일정 수집"""
        results = []

        try:
            # 청약 일정 페이지 (o=k: 청약 예정/진행중)
            self._log_info("청약 일정 수집 시작...")
            url = f"{self.IPO_LIST_URL}?o=k"
            html = self._fetch_page(url)
            results.extend(self._parse_ipo_list(html))

            # 중복 제거 (회사명 + 청약일 기준)
            results = self._filter_valid_ipos(results)

            time.sleep(settings.request_delay)  # 서버 부하 방지

            # 최근 청약 완료 목록도 수집 (o=nw: 신규 상장)
            self._log_info("상장 일정 수집 중...")
            url_nw = f"{self.IPO_LIST_URL}?o=nw"
            html_nw = self._fetch_page(url_nw)
            new_results = self._parse_ipo_list(html_nw, is_listing=True)

            # 기존 데이터와 병합 (회사명 기준)
            results_dict = {r.company_name: r for r in results}
            for ipo in new_results:
                if ipo.company_name in results_dict:
                    # 상장일 정보 업데이트
                    if ipo.listing_date:
                        results_dict[ipo.company_name].listing_date = ipo.listing_date
                else:
                    results.append(ipo)

            # 유효한 데이터만 필터링 (청약일이 있는 것만)
            results = self._filter_valid_ipos(results)

            self._log_info(f"총 {len(results)}건 수집 완료")

        except Exception as e:
            self._log_error(f"수집 실패: {e}")
            raise

        return results

    def _filter_valid_ipos(self, ipos: list[IPOSchedule]) -> list[IPOSchedule]:
        """유효한 IPO 데이터만 필터링"""
        # 제외할 키워드
        invalid_keywords = [
            "실시간",
            "인기주",
            "빨간색",
            "매매",
            "비상장",
            "공모주일정",
            "IPO 청구",
            "IPO 승인",
            "청약일정",
            "신규상장",
            "최근 IPO",
        ]

        valid_ipos = []
        seen_names = set()

        for ipo in ipos:
            # 키워드 필터링
            if any(keyword in ipo.company_name for keyword in invalid_keywords):
                continue

            # 청약일이 없으면 제외
            if not ipo.subscription_start:
                continue

            # 중복 제거 (회사명 + 청약시작일 기준)
            key = f"{ipo.company_name}_{ipo.subscription_start}"
            if key in seen_names:
                continue
            seen_names.add(key)

            valid_ipos.append(ipo)

        return valid_ipos

    def _parse_ipo_list(self, html: str, is_listing: bool = False) -> list[IPOSchedule]:
        """HTML에서 공모주 목록 파싱"""
        results = []
        soup = BeautifulSoup(html, "lxml")

        # 테이블 찾기 (메인 데이터 테이블)
        tables = soup.find_all(
            "table", summary="공모주 소식" if not is_listing else "신규상장종목"
        )
        if not tables:
            tables = soup.find_all("table")

        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cols = row.find_all("td")
                # 신규상장 페이지는 컬럼 수가 다를 수 있음
                min_cols = 5 if not is_listing else 7
                if len(cols) < min_cols:
                    continue

                try:
                    ipo = self._parse_row(cols, is_listing)
                    if ipo:
                        results.append(ipo)
                except Exception as e:
                    logger.debug(f"행 파싱 실패: {e}")
                    continue

        return results

    def _parse_row(self, cols: list, is_listing: bool = False) -> Optional[IPOSchedule]:
        """테이블 행에서 공모주 정보 추출"""
        try:
            if is_listing:
                # 신규상장 페이지 컬럼 구조:
                # [0] 기업명
                # [1] 상장일
                # [2] 현재가(원)
                # [3] 전일대비(%)
                # [4] 공모가(원)
                # [5] 공모가대비 등락률(%)
                # [6] 시초가(원)
                # [7] 시초가대비 등락률(%)
                # [8] 첫날종가(원)
                company_name = self._extract_company_name(cols[0])
                if not company_name:
                    return None

                listing_date_text = cols[1].get_text(strip=True)
                listing_date = self._parse_single_date(
                    listing_date_text.replace("/", ".")
                )

                subscription_start = None
                subscription_end = None

                final_offer_price = self._parse_price(cols[4].get_text(strip=True))
                offer_price_min = None
                offer_price_max = None
                competition = None
                lead_underwriter = None
                detail_url = self._extract_detail_url(cols[0])
            else:
                # 청약 일정 페이지
                # [0] 회사명 (링크)
                # [1] 청약기간
                # [2] 확정공모가
                # [3] 공모가 범위
                # [4] 경쟁률
                # [5] 주관사

                # 회사명 추출
                company_name = self._extract_company_name(cols[0])
                if not company_name:
                    return None

                # 링크 추출
                detail_url = self._extract_detail_url(cols[0])

                # 날짜 정보 추출
                date_text = cols[1].get_text(strip=True)
                subscription_start, subscription_end = self._parse_date_range(date_text)
                listing_date = None

                # 공모가 정보
                final_price_text = cols[2].get_text(strip=True) if len(cols) > 2 else ""
                price_range_text = cols[3].get_text(strip=True) if len(cols) > 3 else ""

                final_offer_price = self._parse_price(final_price_text)
                offer_price_min, offer_price_max = self._parse_price_range(
                    price_range_text
                )

                # 경쟁률
                competition_text = cols[4].get_text(strip=True) if len(cols) > 4 else ""
                competition = self._parse_competition(competition_text)

                # 주관사
                underwriter_text = cols[5].get_text(strip=True) if len(cols) > 5 else ""
                lead_underwriter = self._clean_underwriter(underwriter_text)

            return IPOSchedule(
                company_name=company_name,
                subscription_start=subscription_start,
                subscription_end=subscription_end,
                listing_date=listing_date,
                offer_price_min=offer_price_min,
                offer_price_max=offer_price_max,
                final_offer_price=final_offer_price,
                institutional_competition=competition,
                lead_underwriter=lead_underwriter,
                detail_url=detail_url,
                source=self.source_name,
            )

        except Exception as e:
            logger.debug(f"파싱 오류: {e}")
            return None

    def _extract_company_name(self, cell) -> Optional[str]:
        """셀에서 회사명 추출"""
        # 링크 텍스트 우선
        link = cell.find("a")
        if link:
            text = link.get_text(strip=True)
        else:
            text = cell.get_text(strip=True)

        # 빈 문자열이거나 헤더인 경우 제외
        if not text or text in ["종목명", "기업명", "회사명"]:
            return None

        # (유가), (코넥스), (스팩) 등 태그 제거 및 공백 정리
        text = re.sub(r"\(.*?\)", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text if text else None

    def _extract_detail_url(self, cell) -> Optional[str]:
        """셀에서 상세 페이지 URL 추출"""
        link = cell.find("a")
        if link and link.get("href"):
            href = link["href"]
            if not href.startswith("http"):
                href = f"{self.BASE_URL}{href}"
            return href
        return None

    def _parse_date_range(self, text: str) -> tuple[Optional[date], Optional[date]]:
        """청약 기간 파싱 (예: '2026.01.15~01.16' 또는 '2026.01.15~2026.01.16')"""
        if not text or text == "-":
            return None, None

        # 다양한 구분자 처리
        text = text.replace("~", "~").replace("-", "~").replace("–", "~")

        # 패턴 1: YYYY.MM.DD~MM.DD
        pattern1 = r"(\d{4})\.(\d{1,2})\.(\d{1,2})~(\d{1,2})\.(\d{1,2})"
        match1 = re.search(pattern1, text)
        if match1:
            year = int(match1.group(1))
            start_month = int(match1.group(2))
            start_day = int(match1.group(3))
            end_month = int(match1.group(4))
            end_day = int(match1.group(5))

            try:
                start = date(year, start_month, start_day)
                end = date(year, end_month, end_day)
                # 연도가 넘어가는 경우 (12월~1월)
                if end < start:
                    end = date(year + 1, end_month, end_day)
                return start, end
            except ValueError:
                return None, None

        # 패턴 2: YYYY.MM.DD~YYYY.MM.DD
        pattern2 = r"(\d{4})\.(\d{1,2})\.(\d{1,2})~(\d{4})\.(\d{1,2})\.(\d{1,2})"
        match2 = re.search(pattern2, text)
        if match2:
            try:
                start = date(
                    int(match2.group(1)), int(match2.group(2)), int(match2.group(3))
                )
                end = date(
                    int(match2.group(4)), int(match2.group(5)), int(match2.group(6))
                )
                return start, end
            except ValueError:
                return None, None

        # 패턴 3: 단일 날짜 YYYY.MM.DD
        pattern3 = r"(\d{4})\.(\d{1,2})\.(\d{1,2})"
        match3 = re.search(pattern3, text)
        if match3:
            try:
                single_date = date(
                    int(match3.group(1)), int(match3.group(2)), int(match3.group(3))
                )
                return single_date, single_date
            except ValueError:
                return None, None

        return None, None

    def _parse_single_date(self, text: str) -> Optional[date]:
        """단일 날짜 파싱"""
        if not text or text == "-":
            return None

        pattern = r"(\d{4})\.(\d{1,2})\.(\d{1,2})"
        match = re.search(pattern, text)
        if match:
            try:
                return date(
                    int(match.group(1)), int(match.group(2)), int(match.group(3))
                )
            except ValueError:
                return None
        return None

    def _parse_price(self, text: str) -> Optional[int]:
        """가격 파싱"""
        if not text or text == "-":
            return None

        # 숫자와 쉼표만 추출
        numbers = re.sub(r"[^\d]", "", text)
        if numbers:
            try:
                return int(numbers)
            except ValueError:
                return None
        return None

    def _parse_price_range(self, text: str) -> tuple[Optional[int], Optional[int]]:
        """공모가 범위 파싱 (예: '10,000~12,000')"""
        if not text or text == "-":
            return None, None

        # ~로 분리
        text = text.replace("~", "~").replace("-", "~")
        parts = text.split("~")

        if len(parts) == 2:
            low = self._parse_price(parts[0])
            high = self._parse_price(parts[1])
            return low, high
        elif len(parts) == 1:
            price = self._parse_price(parts[0])
            return price, price

        return None, None

    def _parse_competition(self, text: str) -> Optional[float]:
        """경쟁률 파싱 (예: '967.60:1')"""
        if not text or text == "-":
            return None

        # 숫자:1 패턴 찾기
        pattern = r"([\d,\.]+)\s*:\s*1"
        match = re.search(pattern, text)
        if match:
            try:
                return float(match.group(1).replace(",", ""))
            except ValueError:
                return None
        return None

    def _clean_underwriter(self, text: str) -> Optional[str]:
        """주관사 이름 정리"""
        if not text or text == "-":
            return None

        # 공백 정리
        text = re.sub(r"\s+", " ", text).strip()

        # 첫 번째 주관사만 추출 (대표주관사)
        # 쉼표, 슬래시 등으로 구분된 경우
        for sep in [",", "/", "·", "|"]:
            if sep in text:
                text = text.split(sep)[0].strip()
                break

        return text if text else None

    def collect_detail(self, detail_url: str) -> Optional[dict]:
        """상세 페이지에서 추가 정보 수집 (확장용)"""
        # 필요시 구현: 수요예측 결과, 환불일 등 추가 정보
        pass
