from enum import Enum
from datetime import datetime
from uuid import UUID
from litestar.plugins.sqlalchemy import UUIDAuditBase
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, String, Text, Integer, Boolean, DateTime, Enum as SQLEnum

class MirrorMode(str, Enum):
    ALL_BRANCHES = "ALL_BRANCHES"
    SELECT_BRANCHES = "SELECT_BRANCHES"

class PushMode(str, Enum):
    SAFE = "SAFE"
    FORCE = "FORCE"

class ServiceType(str, Enum):
    SOURCE = "SOURCE"
    TARGET = "TARGET"

class AuthType(str, Enum):
    HTTP_TOKEN = "HTTP_TOKEN"
    SSH_KEY = "SSH_KEY"

class JobStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

class JobType(str, Enum):
    SCHEDULED = "SCHEDULED"
    MANUAL = "MANUAL"

class TriggerOn(str, Enum):
    ALL_FAILURES = "ALL_FAILURES"
    ALL_EVENTS = "ALL_EVENTS"

class GitRepo(UUIDAuditBase):
    __tablename__ = "git_repo"
    repo_name: Mapped[str] = mapped_column(Text, nullable=False)
    source_remote_repo: Mapped[str] = mapped_column(Text, nullable=False)
    target_remote_repo: Mapped[str] = mapped_column(Text, nullable=False)
    ssh_port: Mapped[int] = mapped_column(Integer, nullable=False, default=22)
    replication_interval_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    mirror_mode: Mapped[MirrorMode] = mapped_column(SQLEnum(MirrorMode), default=MirrorMode.ALL_BRANCHES)
    push_mode: Mapped[PushMode] = mapped_column(SQLEnum(PushMode), default=PushMode.SAFE)

    branches: Mapped[list["GitRepoBranch"]] = relationship(back_populates="repo", cascade="all, delete-orphan")
    credentials: Mapped[list["Credentials"]] = relationship(back_populates="repo", cascade="all, delete-orphan")
    jobs: Mapped[list["SyncJob"]] = relationship(back_populates="repo", cascade="all, delete-orphan")

class GitRepoBranch(UUIDAuditBase):
    __tablename__ = "git_repo_branch"
    git_repo_id: Mapped[UUID] = mapped_column(ForeignKey("git_repo.id"), nullable=False)
    branch_name: Mapped[str] = mapped_column(Text, nullable=False)

    repo: Mapped["GitRepo"] = relationship(back_populates="branches")

class Credentials(UUIDAuditBase):
    __tablename__ = "credentials"
    git_repo_id: Mapped[UUID] = mapped_column(ForeignKey("git_repo.id"), nullable=False)
    service_type: Mapped[ServiceType] = mapped_column(SQLEnum(ServiceType), nullable=False)
    auth_type: Mapped[AuthType] = mapped_column(SQLEnum(AuthType), nullable=False)
    encrypted_secret: Mapped[str] = mapped_column(Text, nullable=False)
    username: Mapped[str | None] = mapped_column(Text, nullable=True)

    repo: Mapped["GitRepo"] = relationship(back_populates="credentials")

class SyncJob(UUIDAuditBase):
    __tablename__ = "sync_job"
    git_repo_id: Mapped[UUID] = mapped_column(ForeignKey("git_repo.id"), nullable=False)
    status: Mapped[JobStatus] = mapped_column(SQLEnum(JobStatus), default=JobStatus.PENDING)
    job_type: Mapped[JobType] = mapped_column(SQLEnum(JobType), default=JobType.MANUAL)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    stdout_log: Mapped[str | None] = mapped_column(Text, nullable=True)
    stderr_log: Mapped[str | None] = mapped_column(Text, nullable=True)

    repo: Mapped["GitRepo"] = relationship(back_populates="jobs")

class Webhook(UUIDAuditBase):
    __tablename__ = "webhook"
    url: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    trigger_on: Mapped[TriggerOn] = mapped_column(SQLEnum(TriggerOn), default=TriggerOn.ALL_FAILURES)
