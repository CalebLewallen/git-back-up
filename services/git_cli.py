import subprocess
import os
import shutil
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)

@dataclass
class GitResult:
    returncode: int
    stdout: str
    stderr: str

class GitService:
    def __init__(self, temp_base_dir: str = "/tmp/git-back-up"):
        self.temp_base_dir = Path(temp_base_dir)
        self.temp_base_dir.mkdir(parents=True, exist_ok=True)

    def _run_git(self, args: List[str], cwd: Optional[Path] = None, env: Optional[dict] = None, timeout: int = 1800) -> GitResult:
        full_env = os.environ.copy()
        if env:
            full_env.update(env)
        
        full_env["GIT_TERMINAL_PROMPT"] = "0"
        
        logger.debug(f"Executing git {' '.join(args)} in {cwd or 'default cwd'}")

        try:
            process = subprocess.run(
                ["git"] + args,
                capture_output=True,
                text=True,
                cwd=cwd,
                env=full_env,
                timeout=timeout
            )
            if process.returncode != 0:
                logger.warning(f"Git command failed with code {process.returncode}: {process.stderr}")
            
            return GitResult(
                returncode=process.returncode,
                stdout=process.stdout or "",
                stderr=process.stderr or ""
            )
        except subprocess.TimeoutExpired as e:
            logger.error(f"Git command timed out: {' '.join(args)}")
            stdout = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
            stderr = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
            return GitResult(
                returncode=1,
                stdout=stdout,
                stderr=f"Operation timed out after {timeout} seconds.\n\nSTDERR:\n{stderr}"
            )
        except Exception as e:
            logger.error(f"Unexpected error running git: {e}")
            return GitResult(
                returncode=1,
                stdout="",
                stderr=f"Exception executing git: {str(e)}"
            )

    def mirror_repo(
        self, 
        source_url: str, 
        target_url: str, 
        repo_id: str,
        branches: Optional[List[str]] = None,
        force_push: bool = False,
        source_ssh_key: Optional[str] = None,
        target_ssh_key: Optional[str] = None,
        source_ssh_port: int = 22,
        target_ssh_port: int = 22,
        timeout_seconds: int = 1800
    ) -> GitResult:
        # Check disk space (require at least 500MB free)
        try:
            total, used, free = shutil.disk_usage(self.temp_base_dir)
            if free < 500 * 1024 * 1024:
                msg = f"Insufficient disk space in {self.temp_base_dir}. Only {free // (1024*1024)}MB free."
                logger.error(msg)
                return GitResult(returncode=1, stdout="", stderr=msg)
        except Exception as e:
            logger.warning(f"Failed to check disk usage: {e}")

        repo_dir = self.temp_base_dir / repo_id
        if repo_dir.exists():
            shutil.rmtree(repo_dir, ignore_errors=True)
        
        def get_ssh_env(key_path: Optional[str], port: int):
            if not key_path:
                return {}
            # Use -p flag for custom port support
            return {"GIT_SSH_COMMAND": f"ssh -i {key_path} -p {port} -o StrictHostKeyChecking=no"}

        # 1. Clone/Fetch from Source
        source_env = get_ssh_env(source_ssh_key, source_ssh_port)
        if not branches:
            # Full mirror
            logger.info(f"[{repo_id}] Cloner source: {source_url}")
            res = self._run_git(["clone", "--mirror", source_url, str(repo_dir)], env=source_env, timeout=timeout_seconds)
        else:
            # Selective branches
            logger.info(f"[{repo_id}] Initializing bare repo for selective branches")
            repo_dir.mkdir(parents=True, exist_ok=True)
            res = self._run_git(["init", "--bare"], cwd=repo_dir, env=source_env, timeout=timeout_seconds)
            if res.returncode == 0:
                res = self._run_git(["remote", "add", "origin", source_url], cwd=repo_dir, env=source_env, timeout=timeout_seconds)
            
            if res.returncode == 0:
                for branch in branches:
                    logger.info(f"[{repo_id}] Fetching branch: {branch}")
                    res = self._run_git(["fetch", "origin", f"{branch}:{branch}"], cwd=repo_dir, env=source_env, timeout=timeout_seconds)
                    if res.returncode != 0: break

        if res.returncode != 0:
            logger.error(f"[{repo_id}] Source fetch failed")
            if repo_dir.exists(): shutil.rmtree(repo_dir, ignore_errors=True)
            return res

        # 2. Push to Target
        target_env = get_ssh_env(target_ssh_key, target_ssh_port)
        if not branches:
            push_args = ["push", "--mirror"]
        else:
            push_args = ["push"]
            for branch in branches:
                push_args.append(f"{branch}:{branch}")

        if force_push:
            push_args.append("--force")
        push_args.append(target_url)

        logger.info(f"[{repo_id}] Pushing to target: {target_url}")
        push_res = self._run_git(push_args, cwd=repo_dir, env=target_env, timeout=timeout_seconds)
        
        # Cleanup
        shutil.rmtree(repo_dir, ignore_errors=True)
        
        if push_res.returncode != 0:
            logger.error(f"[{repo_id}] Target push failed")
        else:
            logger.info(f"[{repo_id}] Mirroring completed successfully")
            
        return push_res

git_service = GitService()
