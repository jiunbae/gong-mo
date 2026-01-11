"""
GitHub 퍼블리셔 - Git 커밋 및 푸시
"""

import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class GitHubPublisher:
    """GitHub에 변경사항 커밋 및 푸시"""

    def __init__(self, repo_path: Path, remote: str = "origin", branch: str = "main"):
        self.repo_path = Path(repo_path)
        self.remote = remote
        self.branch = branch

    def publish(self, message: Optional[str] = None) -> bool:
        """변경사항을 커밋하고 푸시"""
        try:
            # 변경사항 확인
            if not self._has_changes():
                logger.info("변경사항 없음, 스킵")
                return True

            # 커밋 메시지 생성
            if not message:
                now = datetime.now().strftime("%Y-%m-%d %H:%M")
                message = f"Update IPO data - {now}"

            # Git add
            self._run_git("add", ".")

            # Git commit
            self._run_git("commit", "-m", message)

            # Git push
            self._run_git("push", self.remote, self.branch)

            logger.info(f"GitHub 푸시 완료: {message}")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Git 작업 실패: {e}")
            return False
        except Exception as e:
            logger.error(f"퍼블리시 실패: {e}")
            return False

    def _has_changes(self) -> bool:
        """변경사항 존재 여부 확인"""
        result = self._run_git("status", "--porcelain", capture=True)
        return bool(result.strip())

    def _run_git(self, *args, capture: bool = False) -> str:
        """Git 명령 실행"""
        cmd = ["git", *args]
        logger.debug(f"실행: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=True,
        )

        if capture:
            return result.stdout
        return ""

    def init_repo(self, remote_url: str) -> bool:
        """Git 저장소 초기화 (docs 폴더용)"""
        try:
            docs_path = self.repo_path

            # .git이 없으면 초기화
            if not (docs_path / ".git").exists():
                self._run_git("init")
                self._run_git("remote", "add", "origin", remote_url)
                logger.info(f"Git 저장소 초기화: {remote_url}")

            return True
        except Exception as e:
            logger.error(f"저장소 초기화 실패: {e}")
            return False
