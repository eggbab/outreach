from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


# ──────────────────────────────────────────────
# Existing tables
# ──────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    plan = Column(
        Enum("free", "personal", "pro", "agency", name="plan_type"),
        default="free",
        nullable=False,
    )
    # Phase 1: trial fields
    trial_started_at = Column(DateTime, nullable=True)
    trial_ends_at = Column(DateTime, nullable=True)
    plan_changed_at = Column(DateTime, nullable=True)
    # Credits for overage billing
    credits = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    email_logs = relationship("EmailLog", back_populates="user", cascade="all, delete-orphan")
    dm_logs = relationship("DmLog", back_populates="user", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(
        Enum("active", "paused", "completed", name="project_status"),
        default="active",
        nullable=False,
    )
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship("User", back_populates="projects")
    keywords = relationship("Keyword", back_populates="project", cascade="all, delete-orphan")
    prospects = relationship("Prospect", back_populates="project", cascade="all, delete-orphan")


class Keyword(Base):
    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    keyword = Column(String(200), nullable=False)
    source = Column(
        Enum("naver", "google", "instagram", "naver_shopping", "naver_map", name="keyword_source"),
        nullable=False,
    )
    created_at = Column(DateTime, default=utcnow, nullable=False)

    project = relationship("Project", back_populates="keywords")


class Prospect(Base):
    __tablename__ = "prospects"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=True)
    email = Column(String(255), nullable=True)
    email_valid = Column(Boolean, nullable=True)
    phone = Column(String(50), nullable=True)
    instagram = Column(String(100), nullable=True)
    website = Column(String(500), nullable=True)
    source = Column(String(50), nullable=True)
    category = Column(String(100), nullable=True)
    # Phase 2: score
    score = Column(Integer, default=0, nullable=False)
    status = Column(
        Enum(
            "collected", "approved", "rejected", "email_sent", "dm_sent",
            name="prospect_status",
        ),
        default="collected",
        nullable=False,
    )
    collected_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    project = relationship("Project", back_populates="prospects")
    email_logs = relationship("EmailLog", back_populates="prospect", cascade="all, delete-orphan")
    dm_logs = relationship("DmLog", back_populates="prospect", cascade="all, delete-orphan")
    notes = relationship("ProspectNote", back_populates="prospect", cascade="all, delete-orphan")
    tags = relationship("ProspectTag", back_populates="prospect", cascade="all, delete-orphan")


class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, index=True)
    prospect_id = Column(Integer, ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sent_at = Column(DateTime, default=utcnow, nullable=False)
    status = Column(
        Enum("success", "failed", name="send_status"),
        nullable=False,
    )
    error_message = Column(Text, nullable=True)
    tracking_id = Column(String(64), unique=True, nullable=True, index=True)
    opened_at = Column(DateTime, nullable=True)
    clicked_at = Column(DateTime, nullable=True)
    # Phase 3: A/B + sequence
    variant_id = Column(Integer, ForeignKey("email_variants.id", ondelete="SET NULL"), nullable=True)
    sequence_step_id = Column(Integer, ForeignKey("email_sequence_steps.id", ondelete="SET NULL"), nullable=True)

    prospect = relationship("Prospect", back_populates="email_logs")
    user = relationship("User", back_populates="email_logs")


class DmLog(Base):
    __tablename__ = "dm_logs"

    id = Column(Integer, primary_key=True, index=True)
    prospect_id = Column(Integer, ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sent_at = Column(DateTime, default=utcnow, nullable=False)
    status = Column(
        Enum("success", "failed", name="dm_send_status"),
        nullable=False,
    )
    error_message = Column(Text, nullable=True)

    prospect = relationship("Prospect", back_populates="dm_logs")
    user = relationship("User", back_populates="dm_logs")


class EmailSendJob(Base):
    __tablename__ = "email_send_jobs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), default="running", nullable=False)
    total_targets = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    current_email = Column(String(255), nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime, default=utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)


class CollectionJob(Base):
    __tablename__ = "collection_jobs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), default="running", nullable=False)
    total_tasks = Column(Integer, default=0)
    processed_tasks = Column(Integer, default=0)
    prospects_found = Column(Integer, default=0)
    current_task = Column(String(300), nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime, default=utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    gmail_email = Column(String(255), nullable=True)
    gmail_app_password_encrypted = Column(String(500), nullable=True)
    email_template = Column(Text, nullable=True)
    dm_template = Column(Text, nullable=True)
    daily_email_limit = Column(Integer, default=80, nullable=False)
    daily_dm_limit = Column(Integer, default=15, nullable=False)

    __table_args__ = (UniqueConstraint("user_id", name="uq_user_settings_user_id"),)

    user = relationship("User", back_populates="settings")


# ──────────────────────────────────────────────
# Phase 1: Usage & Subscriptions
# ──────────────────────────────────────────────

class UsageRecord(Base):
    __tablename__ = "usage_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False, default=date.today)
    emails_sent = Column(Integer, default=0, nullable=False)
    dms_sent = Column(Integer, default=0, nullable=False)
    prospects_collected = Column(Integer, default=0, nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_usage_user_date"),)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    plan = Column(
        Enum("free", "pro", "agency", name="subscription_plan"),
        default="free",
        nullable=False,
    )
    status = Column(
        Enum("active", "cancelled", "trialing", name="subscription_status"),
        default="active",
        nullable=False,
    )
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False, nullable=False)


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Integer, nullable=False)  # positive=charge, negative=deduct
    balance_after = Column(Integer, nullable=False)
    description = Column(String(300), nullable=False)
    tx_type = Column(String(20), nullable=False)  # purchase, deduct, bonus, refund
    created_at = Column(DateTime, default=utcnow, nullable=False)


# ──────────────────────────────────────────────
# Phase 2: Notes, Tags
# ──────────────────────────────────────────────

class ProspectNote(Base):
    __tablename__ = "prospect_notes"

    id = Column(Integer, primary_key=True, index=True)
    prospect_id = Column(Integer, ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    prospect = relationship("Prospect", back_populates="notes")


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(50), nullable=False)
    color = Column(String(20), default="#3B82F6", nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_tag_user_name"),)

    prospect_tags = relationship("ProspectTag", back_populates="tag", cascade="all, delete-orphan")


class ProspectTag(Base):
    __tablename__ = "prospect_tags"

    id = Column(Integer, primary_key=True, index=True)
    prospect_id = Column(Integer, ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False)
    tag_id = Column(Integer, ForeignKey("tags.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (UniqueConstraint("prospect_id", "tag_id", name="uq_prospect_tag"),)

    prospect = relationship("Prospect", back_populates="tags")
    tag = relationship("Tag", back_populates="prospect_tags")


# ──────────────────────────────────────────────
# Phase 3: Email Templates, Variants, Sequences
# ──────────────────────────────────────────────

class EmailTemplate(Base):
    __tablename__ = "email_templates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    subject = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    variants = relationship("EmailVariant", back_populates="template", cascade="all, delete-orphan")


class EmailVariant(Base):
    __tablename__ = "email_variants"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("email_templates.id", ondelete="CASCADE"), nullable=False)
    variant_name = Column(String(10), default="A", nullable=False)
    subject = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)
    weight = Column(Integer, default=50, nullable=False)

    template = relationship("EmailTemplate", back_populates="variants")


class EmailSequence(Base):
    __tablename__ = "email_sequences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    status = Column(
        Enum("active", "paused", "draft", name="sequence_status"),
        default="draft",
        nullable=False,
    )
    created_at = Column(DateTime, default=utcnow, nullable=False)

    steps = relationship("EmailSequenceStep", back_populates="sequence", cascade="all, delete-orphan")
    enrollments = relationship("SequenceEnrollment", back_populates="sequence", cascade="all, delete-orphan")


class EmailSequenceStep(Base):
    __tablename__ = "email_sequence_steps"

    id = Column(Integer, primary_key=True, index=True)
    sequence_id = Column(Integer, ForeignKey("email_sequences.id", ondelete="CASCADE"), nullable=False)
    step_number = Column(Integer, nullable=False)
    delay_days = Column(Integer, default=1, nullable=False)
    subject = Column(String(500), nullable=False)
    body = Column(Text, nullable=False)
    send_condition = Column(
        Enum("always", "not_opened", "not_clicked", name="send_condition"),
        default="always",
        nullable=False,
    )

    sequence = relationship("EmailSequence", back_populates="steps")


class SequenceEnrollment(Base):
    __tablename__ = "sequence_enrollments"

    id = Column(Integer, primary_key=True, index=True)
    sequence_id = Column(Integer, ForeignKey("email_sequences.id", ondelete="CASCADE"), nullable=False)
    prospect_id = Column(Integer, ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False)
    current_step = Column(Integer, default=1, nullable=False)
    status = Column(
        Enum("active", "completed", "paused", name="enrollment_status"),
        default="active",
        nullable=False,
    )
    last_step_sent_at = Column(DateTime, nullable=True)
    next_send_at = Column(DateTime, nullable=True)
    enrolled_at = Column(DateTime, default=utcnow, nullable=False)

    sequence = relationship("EmailSequence", back_populates="enrollments")


# ──────────────────────────────────────────────
# Phase 4: Pipeline, Deals, Calls, Activities, Proposals, Meetings
# ──────────────────────────────────────────────

class PipelineStage(Base):
    __tablename__ = "pipeline_stages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    position = Column(Integer, default=0, nullable=False)
    color = Column(String(20), default="#3B82F6", nullable=False)
    is_won = Column(Boolean, default=False, nullable=False)
    is_lost = Column(Boolean, default=False, nullable=False)

    deals = relationship("Deal", back_populates="stage")


class Deal(Base):
    __tablename__ = "deals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    prospect_id = Column(Integer, ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    stage_id = Column(Integer, ForeignKey("pipeline_stages.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(300), nullable=False)
    value = Column(Integer, default=0, nullable=False)  # KRW
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    closed_at = Column(DateTime, nullable=True)

    stage = relationship("PipelineStage", back_populates="deals")


class CallLog(Base):
    __tablename__ = "call_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    prospect_id = Column(Integer, ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    call_type = Column(
        Enum("outbound", "inbound", "missed", name="call_type"),
        default="outbound",
        nullable=False,
    )
    duration_seconds = Column(Integer, default=0, nullable=False)
    notes = Column(Text, nullable=True)
    outcome = Column(String(100), nullable=True)
    callback_at = Column(DateTime, nullable=True)
    called_at = Column(DateTime, default=utcnow, nullable=False)


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    prospect_id = Column(Integer, ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False)
    activity_type = Column(
        Enum(
            "email_sent", "email_opened", "email_clicked",
            "dm_sent", "call", "note", "deal_created",
            "deal_stage_changed", "meeting_booked", "proposal_sent",
            name="activity_type",
        ),
        nullable=False,
    )
    reference_id = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class Proposal(Base):
    __tablename__ = "proposals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    prospect_id = Column(Integer, ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False)
    deal_id = Column(Integer, ForeignKey("deals.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(300), nullable=False)
    content_html = Column(Text, nullable=False)
    total_amount = Column(Integer, default=0, nullable=False)
    status = Column(
        Enum("draft", "sent", "viewed", "accepted", name="proposal_status"),
        default="draft",
        nullable=False,
    )
    tracking_id = Column(String(64), unique=True, nullable=True, index=True)
    sent_at = Column(DateTime, nullable=True)
    viewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class ProposalTemplate(Base):
    __tablename__ = "proposal_templates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    content_html = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class MeetingSlot(Base):
    __tablename__ = "meeting_slots"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    duration_minutes = Column(Integer, default=30, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    prospect_id = Column(Integer, ForeignKey("prospects.id", ondelete="SET NULL"), nullable=True)
    booking_code = Column(String(64), unique=True, nullable=False, index=True)
    title = Column(String(300), nullable=False)
    scheduled_at = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=30, nullable=False)
    status = Column(
        Enum("scheduled", "completed", "cancelled", name="meeting_status"),
        default="scheduled",
        nullable=False,
    )
    booker_name = Column(String(100), nullable=True)
    booker_email = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)


# ──────────────────────────────────────────────
# Phase 5: Onboarding, Teams, API Keys
# ──────────────────────────────────────────────

class OnboardingProgress(Base):
    __tablename__ = "onboarding_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    steps_completed = Column(Text, default="[]", nullable=False)  # JSON string
    completed_at = Column(DateTime, nullable=True)
    dismissed = Column(Boolean, default=False, nullable=False)


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")


class TeamMember(Base):
    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(
        Enum("admin", "member", name="team_role"),
        default="member",
        nullable=False,
    )

    __table_args__ = (UniqueConstraint("team_id", "user_id", name="uq_team_member"),)

    team = relationship("Team", back_populates="members")


class TeamProject(Base):
    __tablename__ = "team_projects"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    __table_args__ = (UniqueConstraint("team_id", "project_id", name="uq_team_project"),)


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    key_hash = Column(String(255), nullable=False)
    key_prefix = Column(String(10), nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
