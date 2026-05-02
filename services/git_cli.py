import subprocess
import os
import shutil
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

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

        try:
            process = subprocess.run(
                ["git"] + args,
                capture_output=True,
                text=True,
                cwd=cwd,
                env=full_env,
                timeout=timeout
            )
            return GitResult(
                returncode=process.returncode,
                stdout=process.stdout,
                stderr=process.stderr
            )
        except subprocess.TimeoutExpired as e:
            return GitResult(
                returncode=1,
                stdout=e.stdout if e.stdout else "",
                stderr=f"Operation timed out after {timeout} seconds. {e.stderr if e.stderr else ''}"
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
        timeout_seconds: int = 1800
    ) -> GitResult:
        # Check disk space (require at least 500MB free)
        total, used, free = shutil.disk_usage(self.temp_base_dir)
        if free < 500 * 1024 * 1024:
            return GitResult(
                returncode=1,
                stdout="",
                stderr=f"Insufficient disk space in {self.temp_base_dir}. Only {free // (1024*1024)}MB free."
            )

        repo_dir = self.temp_base_dir / repo_id
        if repo_dir.exists():
            shutil.rmtree(repo_dir, ignore_errors=True)
        
        def get_ssh_env(key_path: Optional[str]):
            if not key_path:
                return {}
            return {"GIT_SSH_COMMAND": f"ssh -i {key_path} -o StrictHostKeyChecking=no"}

        # 1. Clone/Fetch from Source
        source_env = get_ssh_env(source_ssh_key)
        if not branches:
            # Full mirror
            res = self._run_git(["clone", "--mirror", source_url, str(repo_dir)], env=source_env, timeout=timeout_seconds)
        else:
            # Selective branches
            repo_dir.mkdir()
            res = self._run_git(["init", "--bare"], cwd=repo_dir, env=source_env, timeout=timeout_seconds)
            if res.returncode == 0:
                res = self._run_git(["remote", "add", "origin", source_url], cwd=repo_dir, env=source_env, timeout=timeout_seconds)
            
            if res.returncode == 0:
                for branch in branches:
                    res = self._run_git(["fetch", "origin", f"{branch}:{branch}"], cwd=repo_dir, env=source_env, timeout=timeout_seconds)
                    if res.returncode != 0: break

        if res.returncode != 0:
            if repo_dir.exists(): shutil.rmtree(repo_dir, ignore_errors=True)
            return res

        # 2. Push to Target
        target_env = get_ssh_env(target_ssh_key)
        if not branches:
            push_args = ["push", "--mirror"]
        else:
            push_args = ["push"]
            for branch in branches:
                push_args.append(f"{branch}:{branch}")

        if force_push:
            push_args.append("--force")
        push_args.append(target_url)

        push_res = self._run_git(push_args, cwd=repo_dir, env=target_env, timeout=timeout_seconds)
        
        # Cleanup
        shutil.rmtree(repo_dir, ignore_errors=True)
        
        return push_res

git_service = GitService()
