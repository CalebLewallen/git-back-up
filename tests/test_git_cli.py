import pytest
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch
from services.git_cli import GitService

@pytest.fixture
def git_service(tmp_path):
    return GitService(temp_base_dir=str(tmp_path))

def test_run_git_success(git_service):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="success", stderr="")
        res = git_service._run_git(["status"])
        assert res.returncode == 0
        assert res.stdout == "success"
        mock_run.assert_called_once()

def test_run_git_timeout(git_service):
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["git"], timeout=30)
        res = git_service._run_git(["fetch"])
        assert res.returncode == 1
        assert "timed out" in res.stderr

def test_mirror_repo_full(git_service, mocker):
    mocker.patch("shutil.disk_usage", return_value=(1000, 500, 1000 * 1024 * 1024))
    with patch.object(git_service, "_run_git") as mock_run_git:
        mock_run_git.return_value = MagicMock(returncode=0)
        
        res = git_service.mirror_repo(
            source_url="https://src.com",
            target_url="https://dst.com",
            repo_id="test-repo"
        )
        
        assert res.returncode == 0
        # Should call clone --mirror and then push --mirror
        assert mock_run_git.call_count == 2
        args1 = mock_run_git.call_args_list[0][0][0]
        assert "clone" in args1
        assert "--mirror" in args1
        
        args2 = mock_run_git.call_args_list[1][0][0]
        assert "push" in args2
        assert "--mirror" in args2

def test_mirror_repo_insufficient_space(git_service, mocker):
    mocker.patch("shutil.disk_usage", return_value=(1000, 999, 100)) # 100 bytes free
    res = git_service.mirror_repo("s", "t", "id")
    assert res.returncode == 1
    assert "Insufficient disk space" in res.stderr

def test_ssh_key_usage(git_service, mocker):
    mocker.patch("shutil.disk_usage", return_value=(1000, 500, 1000 * 1024 * 1024))
    with patch.object(git_service, "_run_git") as mock_run_git:
        mock_run_git.return_value = MagicMock(returncode=0)
        
        git_service.mirror_repo(
            source_url="s", target_url="t", repo_id="id",
            source_ssh_key="/path/to/source_key",
            target_ssh_key="/path/to/target_key"
        )
        
        # Check source env
        source_call_env = mock_run_git.call_args_list[0][1]["env"]
        assert "GIT_SSH_COMMAND" in source_call_env
        assert "/path/to/source_key" in source_call_env["GIT_SSH_COMMAND"]
        
        # Check target env
        target_call_env = mock_run_git.call_args_list[1][1]["env"]
        assert "GIT_SSH_COMMAND" in target_call_env
        assert "/path/to/target_key" in target_call_env["GIT_SSH_COMMAND"]
