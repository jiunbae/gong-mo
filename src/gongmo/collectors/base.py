"""
크롤러 베이스 클래스
"""

from abc import ABC, abstractmethod
from typing import Optional
import logging

from ..models.ipo import IPOSchedule

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """공모주 정보 수집기 베이스 클래스"""

    source_name: str = "unknown"

    @abstractmethod
    def collect(self) -> list[IPOSchedule]:
        """공모주 정보 수집"""
        pass

    def _log_info(self, message: str):
        logger.info(f"[{self.source_name}] {message}")

    def _log_error(self, message: str):
        logger.error(f"[{self.source_name}] {message}")

    def _log_warning(self, message: str):
        logger.warning(f"[{self.source_name}] {message}")
