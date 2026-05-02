from litestar.plugins.sqlalchemy import UUIDAuditBase
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, String, Text, Integer, Boolean

class GitRepo(UUIDAuditBase):
    __tablename__ = "git_repo"
    repo_name: Mapped[str] = mapped_column(Text, nullable=False)
    source_remote_repo: Mapped[str] = mapped_column(Text, nullable=False)
    target_remote_repo: Mapped[str] = mapped_column(Text, nullable=False)
    replication_internal_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)