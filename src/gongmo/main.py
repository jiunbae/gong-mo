"""
공모주 캘린더 봇 - 메인 실행 파일
"""

import argparse
import logging
import sys
from datetime import datetime

from pathlib import Path

from .collectors.site38 import Site38Collector
from .calendar.client import GoogleCalendarClient, SyncAction
from .calendar.auth import GoogleCalendarAuth
from .models.ipo import IPOSchedule
from .config import settings, CREDENTIALS_PATH, BASE_DIR
from .publisher.static import StaticSiteGenerator
from .publisher.github import GitHubPublisher

# 로깅 설정
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class IPOCalendarBot:
    """공모주 캘린더 봇 메인 클래스"""

    def __init__(self):
        self.collector = Site38Collector()
        self.calendar_client: GoogleCalendarClient = None

    def run(self, dry_run: bool = False) -> dict:
        """전체 파이프라인 실행"""
        logger.info("=" * 50)
        logger.info("공모주 캘린더 봇 시작")
        logger.info("=" * 50)

        stats = {
            "collected": 0,
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0,
        }

        try:
            # 1. 공모주 정보 수집
            logger.info("\n[1/3] 공모주 정보 수집 중...")
            ipo_list = self.collector.collect()
            stats["collected"] = len(ipo_list)
            logger.info(f"  -> {len(ipo_list)}건 수집 완료")

            if not ipo_list:
                logger.warning("수집된 공모주 정보가 없습니다.")
                return stats

            # 수집된 정보 출력
            self._print_ipo_list(ipo_list)

            if dry_run:
                logger.info("\n[DRY RUN] 캘린더 등록을 건너뜁니다.")
                return stats

            # 2. Google Calendar 인증
            logger.info("\n[2/3] Google Calendar 연결 중...")
            self.calendar_client = GoogleCalendarClient()

            # 캘린더 정보 확인
            calendar_info = self.calendar_client.get_calendar_info()
            if calendar_info:
                logger.info(f"  -> 캘린더: {calendar_info.get('summary', 'Unknown')}")
            else:
                logger.error("  -> 캘린더 연결 실패")
                return stats

            # 3. 캘린더 동기화
            logger.info("\n[3/3] 캘린더 동기화 중...")
            for ipo in ipo_list:
                results = self.calendar_client.sync_ipo(ipo)

                for result in results:
                    if result.action == SyncAction.CREATE:
                        stats["created"] += 1
                    elif result.action == SyncAction.UPDATE:
                        stats["updated"] += 1
                    elif result.action == SyncAction.SKIP:
                        stats["skipped"] += 1
                    elif result.action == SyncAction.ERROR:
                        stats["errors"] += 1

            # 결과 요약
            self._print_summary(stats)

        except FileNotFoundError as e:
            logger.error(f"\n인증 파일 오류: {e}")
            logger.info("\n설정 방법:")
            logger.info("1. Google Cloud Console에서 프로젝트 생성")
            logger.info("2. Calendar API 활성화")
            logger.info("3. OAuth 2.0 자격 증명 생성")
            logger.info(f"4. credentials.json 파일을 {CREDENTIALS_PATH}에 저장")
            stats["errors"] += 1

        except Exception as e:
            logger.error(f"\n실행 중 오류 발생: {e}")
            stats["errors"] += 1
            raise

        return stats

    def _print_ipo_list(self, ipo_list: list[IPOSchedule]):
        """수집된 공모주 목록 출력"""
        logger.info("\n--- 수집된 공모주 목록 ---")
        for i, ipo in enumerate(ipo_list, 1):
            logger.info(f"  {i}. {ipo}")

    def _print_summary(self, stats: dict):
        """결과 요약 출력"""
        logger.info("\n" + "=" * 50)
        logger.info("동기화 완료!")
        logger.info(f"  - 수집: {stats['collected']}건")
        logger.info(f"  - 생성: {stats['created']}건")
        logger.info(f"  - 수정: {stats['updated']}건")
        logger.info(f"  - 스킵: {stats['skipped']}건")
        if stats["errors"] > 0:
            logger.info(f"  - 오류: {stats['errors']}건")
        logger.info("=" * 50)

    def list_events(self, limit: int = 10):
        """등록된 공모주 이벤트 목록 조회"""
        logger.info("등록된 공모주 이벤트 조회 중...")

        self.calendar_client = GoogleCalendarClient()
        events = self.calendar_client.list_upcoming_events(max_results=limit)

        if not events:
            logger.info("등록된 공모주 이벤트가 없습니다.")
            return

        logger.info(f"\n다가오는 공모주 일정 ({len(events)}건):")
        for event in events:
            start = event.get("start", {}).get(
                "date", event.get("start", {}).get("dateTime", "")
            )
            summary = event.get("summary", "Unknown")
            logger.info(f"  - [{start}] {summary}")

    def check_auth(self) -> bool:
        """인증 상태 확인"""
        auth = GoogleCalendarAuth()
        if auth.is_authenticated():
            logger.info("Google Calendar 인증 완료 상태입니다.")
            return True
        else:
            logger.info("Google Calendar 인증이 필요합니다.")
            return False

    def cleanup_calendar(self, company_name: str = None) -> dict:
        """캘린더 이벤트 정리

        Args:
            company_name: 특정 회사만 정리. None이면 전체 정리.
        """
        logger.info("=" * 50)
        if company_name:
            logger.info(f"'{company_name}' 이벤트 정리 시작")
        else:
            logger.info("전체 이벤트 정리 시작")
        logger.info("=" * 50)

        stats = {"deleted": 0, "errors": 0}

        self.calendar_client = GoogleCalendarClient()

        if company_name:
            results = self.calendar_client.cleanup_company_events(company_name)
        else:
            results = self.calendar_client.cleanup_all_events()

        for result in results:
            if result.action == SyncAction.DELETE:
                stats["deleted"] += 1
                logger.info(f"  삭제: {result.event_title}")
            elif result.action == SyncAction.ERROR:
                stats["errors"] += 1
                logger.error(f"  오류: {result.event_title} - {result.error}")

        logger.info("\n" + "=" * 50)
        logger.info(f"정리 완료: 삭제 {stats['deleted']}건, 오류 {stats['errors']}건")
        logger.info("=" * 50)

        return stats

    def resync_calendar(self) -> dict:
        """캘린더 전체 재동기화 (정리 후 다시 등록)"""
        logger.info("=" * 50)
        logger.info("캘린더 전체 재동기화 시작")
        logger.info("=" * 50)

        # 1. 기존 이벤트 모두 삭제
        logger.info("\n[1/3] 기존 이벤트 정리 중...")
        cleanup_stats = self.cleanup_calendar()

        # 2. 공모주 정보 새로 수집
        logger.info("\n[2/3] 공모주 정보 수집 중...")
        ipo_list = self.collector.collect(verify_details=True)
        logger.info(f"  -> {len(ipo_list)}건 수집 완료")

        # 3. 캘린더 동기화
        logger.info("\n[3/3] 캘린더 재등록 중...")
        stats = {
            "cleaned": cleanup_stats["deleted"],
            "collected": len(ipo_list),
            "created": 0,
            "errors": cleanup_stats["errors"],
        }

        if not self.calendar_client:
            self.calendar_client = GoogleCalendarClient()

        for ipo in ipo_list:
            results = self.calendar_client.sync_ipo(ipo)
            for result in results:
                if result.action == SyncAction.CREATE:
                    stats["created"] += 1
                elif result.action == SyncAction.ERROR:
                    stats["errors"] += 1

        logger.info("\n" + "=" * 50)
        logger.info("재동기화 완료!")
        logger.info(f"  - 정리: {stats['cleaned']}건")
        logger.info(f"  - 수집: {stats['collected']}건")
        logger.info(f"  - 생성: {stats['created']}건")
        if stats["errors"] > 0:
            logger.warning(f"  - 오류: {stats['errors']}건")
        logger.info("=" * 50)

        return stats

    def publish_site(self, push: bool = True) -> dict:
        """정적 사이트 데이터 생성 및 GitHub 푸시"""
        logger.info("=" * 50)
        logger.info("정적 사이트 업데이트 시작")
        logger.info("=" * 50)

        stats = {
            "collected": 0,
            "published": False,
            "pushed": False,
        }

        try:
            # 1. 공모주 정보 수집
            logger.info("\n[1/3] 공모주 정보 수집 중...")
            ipo_list = self.collector.collect()
            stats["collected"] = len(ipo_list)
            logger.info(f"  -> {len(ipo_list)}건 수집 완료")

            if not ipo_list:
                logger.warning("수집된 공모주 정보가 없습니다.")
                return stats

            # 2. 정적 사이트 데이터 생성
            logger.info("\n[2/3] 정적 사이트 데이터 생성 중...")
            docs_dir = BASE_DIR / "docs"
            generator = StaticSiteGenerator(docs_dir)
            data_path = generator.generate(ipo_list)
            stats["published"] = True
            logger.info(f"  -> {data_path} 생성 완료")

            # 3. GitHub 푸시
            if push:
                logger.info("\n[3/3] GitHub 푸시 중...")
                publisher = GitHubPublisher(docs_dir)
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                message = f"Update IPO data ({len(ipo_list)}건) - {now}"

                if publisher.publish(message):
                    stats["pushed"] = True
                    logger.info("  -> GitHub 푸시 완료")
                else:
                    logger.warning("  -> GitHub 푸시 실패 또는 변경사항 없음")
            else:
                logger.info("\n[3/3] GitHub 푸시 스킵 (--no-push)")

            # 결과 요약
            logger.info("\n" + "=" * 50)
            logger.info("정적 사이트 업데이트 완료!")
            logger.info(f"  - 수집: {stats['collected']}건")
            logger.info(f"  - 데이터 생성: {'성공' if stats['published'] else '실패'}")
            logger.info(
                f"  - GitHub 푸시: {'성공' if stats['pushed'] else '스킵/실패'}"
            )
            logger.info("=" * 50)

        except Exception as e:
            logger.error(f"\n정적 사이트 업데이트 실패: {e}")
            raise

        return stats


def main():
    """CLI 진입점"""
    parser = argparse.ArgumentParser(
        description="공모주 일정을 구글 캘린더에 자동 등록하는 봇",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  gongmo                    # 공모주 수집 및 캘린더 등록
  gongmo --dry-run          # 수집만 하고 캘린더 등록 안 함
  gongmo --list             # 등록된 이벤트 목록 조회
  gongmo --check-auth       # 인증 상태 확인
  gongmo --publish          # 정적 사이트 업데이트 및 GitHub 푸시
  gongmo --publish --no-push # 정적 사이트만 생성 (푸시 안 함)
  gongmo --cleanup          # 캘린더의 모든 공모주 이벤트 삭제
  gongmo --cleanup "회사명"  # 특정 회사 이벤트만 삭제
  gongmo --resync           # 전체 재동기화 (삭제 후 재등록)
        """,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="캘린더 등록 없이 수집만 실행",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="등록된 공모주 이벤트 목록 조회",
    )
    parser.add_argument(
        "--check-auth",
        action="store_true",
        help="Google Calendar 인증 상태 확인",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="상세 로그 출력",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="정적 사이트 데이터 생성 및 GitHub 푸시",
    )
    parser.add_argument(
        "--no-push",
        action="store_true",
        help="--publish 시 GitHub 푸시 안 함",
    )
    parser.add_argument(
        "--cleanup",
        nargs="?",
        const="__ALL__",
        metavar="회사명",
        help="캘린더 이벤트 정리 (회사명 지정 시 해당 회사만)",
    )
    parser.add_argument(
        "--resync",
        action="store_true",
        help="캘린더 전체 재동기화 (기존 삭제 후 재등록)",
    )

    args = parser.parse_args()

    # 상세 로그 모드
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    bot = IPOCalendarBot()

    try:
        if args.check_auth:
            bot.check_auth()
        elif args.list:
            bot.list_events()
        elif args.publish:
            bot.publish_site(push=not args.no_push)
        elif args.cleanup:
            company = None if args.cleanup == "__ALL__" else args.cleanup
            stats = bot.cleanup_calendar(company_name=company)
            if stats["errors"] > 0:
                sys.exit(1)
        elif args.resync:
            stats = bot.resync_calendar()
            if stats["errors"] > 0:
                sys.exit(1)
        else:
            stats = bot.run(dry_run=args.dry_run)
            # 오류가 있으면 종료 코드 1
            if stats["errors"] > 0:
                sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\n중단됨")
        sys.exit(130)
    except Exception as e:
        logger.error(f"오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
