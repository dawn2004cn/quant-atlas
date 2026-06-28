from __future__ import annotations

"""ORM models for Moments / Friend-circle posts and interactions."""


from sqlalchemy import BIGINT, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..orm import Base


class MomentPost(Base):
    __tablename__ = "moments_posts"

    post_id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(64), nullable=False)
    author_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_json: Mapped[str | None] = mapped_column(Text)
    market_date: Mapped[str | None] = mapped_column(String(16))
    created_at: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    attachments: Mapped[list[MomentAttachment]] = relationship(
        "MomentAttachment", back_populates="post", cascade="all, delete-orphan", lazy="selectin"
    )
    likes: Mapped[list[MomentLike]] = relationship(
        "MomentLike", back_populates="post", cascade="all, delete-orphan", lazy="selectin"
    )
    comments: Mapped[list[MomentComment]] = relationship(
        "MomentComment", back_populates="post", cascade="all, delete-orphan", lazy="selectin"
    )


class MomentAttachment(Base):
    __tablename__ = "moments_attachments"

    attachment_id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("moments_posts.post_id", ondelete="CASCADE"), nullable=False, index=True)
    media_type: Mapped[str] = mapped_column(String(16), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(128))
    size_bytes: Mapped[int] = mapped_column(BIGINT, default=0)
    meta_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False)

    post: Mapped[MomentPost] = relationship("MomentPost", back_populates="attachments")


class MomentLike(Base):
    __tablename__ = "moments_likes"

    like_id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("moments_posts.post_id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False)

    post: Mapped[MomentPost] = relationship("MomentPost", back_populates="likes")


class MomentComment(Base):
    __tablename__ = "moments_comments"

    comment_id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("moments_posts.post_id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    author_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False)

    post: Mapped[MomentPost] = relationship("MomentPost", back_populates="comments")
