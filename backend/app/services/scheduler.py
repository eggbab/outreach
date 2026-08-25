import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.database import SessionLocal

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def expire_trials():
    """Downgrade users whose trial has expired."""
    db = SessionLocal()
    try:
        from app.models.models import User

        now = datetime.now(timezone.utc)
        expired_users = (
            db.query(User)
            .filter(
                User.trial_ends_at.isnot(None),
                User.trial_ends_at <= now,
                User.plan != "free",
            )
            .all()
        )
        for user in expired_users:
            logger.info(f"Trial expired for user {user.id} ({user.email}), downgrading to free")
            user.plan = "free"
            user.trial_ends_at = None
            user.plan_changed_at = now
        db.commit()
        if expired_users:
            logger.info(f"Downgraded {len(expired_users)} users with expired trials")
    except Exception as e:
        logger.error(f"Error in expire_trials job: {e}")
        db.rollback()
    finally:
        db.close()


def process_sequences():
    """Process email sequence enrollments and send due emails."""
    db = SessionLocal()
    try:
        from app.models.models import (
            EmailLog, EmailSequence, EmailSequenceStep,
            Prospect, SequenceEnrollment, UserSettings,
        )
        from app.core.security import decrypt_value
        from app.services.sender.email import send_email

        now = datetime.now(timezone.utc)
        due_enrollments = (
            db.query(SequenceEnrollment)
            .filter(
                SequenceEnrollment.status == "active",
                SequenceEnrollment.next_send_at <= now,
            )
            .limit(50)
            .all()
        )

        for enrollment in due_enrollments:
            sequence = db.query(EmailSequence).filter(EmailSequence.id == enrollment.sequence_id).first()
            if not sequence or sequence.status != "active":
                continue

            step = (
                db.query(EmailSequenceStep)
                .filter(
                    EmailSequenceStep.sequence_id == sequence.id,
                    EmailSequenceStep.step_number == enrollment.current_step,
                )
                .first()
            )
            if not step:
                enrollment.status = "completed"
                continue

            prospect = db.query(Prospect).filter(Prospect.id == enrollment.prospect_id).first()
            if not prospect or not prospect.email:
                enrollment.status = "completed"
                continue

            # Check send condition
            if step.send_condition != "always":
                last_log = (
                    db.query(EmailLog)
                    .filter(
                        EmailLog.prospect_id == prospect.id,
                        EmailLog.sequence_step_id.isnot(None),
                    )
                    .order_by(EmailLog.sent_at.desc())
                    .first()
                )
                if last_log:
                    if step.send_condition == "not_opened" and last_log.opened_at:
                        enrollment.status = "completed"
                        continue
                    if step.send_condition == "not_clicked" and last_log.clicked_at:
                        enrollment.status = "completed"
                        continue

            # 답장한 잠재고객에게는 후속 메일 중단 (딜 보호)
            if prospect.status == "replied":
                enrollment.status = "stopped"
                continue

            settings = db.query(UserSettings).filter(UserSettings.user_id == sequence.user_id).first()
            if not settings or not settings.gmail_email or not settings.gmail_app_password_encrypted:
                continue

            # 수신거부/블랙리스트 차단
            from app.services.compliance import (
                apply_ad_prefix,
                build_compliance_footer,
                build_list_unsubscribe_headers,
                inject_compliance_footer,
                is_email_suppressed,
            )
            if is_email_suppressed(db, sequence.user_id, prospect.email):
                enrollment.status = "stopped"
                continue

            # 크레딧 확인 — 부족하면 이번 턴은 건너뜀 (다음 폴링에서 재시도)
            from app.core.plans import CREDIT_COSTS, check_credits, deduct_credits
            if not check_credits(db, sequence.user_id, "email", 1)["allowed"]:
                continue

            try:
                gmail_pw = decrypt_value(settings.gmail_app_password_encrypted)
                subject = step.subject.replace("{company_name}", prospect.name or "")
                body = step.body.replace("{company_name}", prospect.name or "")

                import secrets
                tracking_id = secrets.token_hex(16)

                # 컴플라이언스: (광고) 표기 + 전송자 정보/수신거부 푸터 + 추적 픽셀
                from app.core.config import settings as app_settings
                subject = apply_ad_prefix(subject, settings.ad_prefix_enabled)
                body = inject_compliance_footer(
                    body, build_compliance_footer(tracking_id, settings.sender_info)
                )
                pixel = (
                    f'<img src="{app_settings.BASE_URL}/api/t/open/{tracking_id}" '
                    f'width="1" height="1" style="display:none">'
                )
                body = body.replace("</body>", f"{pixel}\n</body>", 1) if "</body>" in body else body + pixel

                success = send_email(
                    gmail_email=settings.gmail_email,
                    gmail_app_password=gmail_pw,
                    to_email=prospect.email,
                    subject=subject,
                    html_body=body,
                    extra_headers=build_list_unsubscribe_headers(tracking_id),
                )

                log = EmailLog(
                    prospect_id=prospect.id,
                    user_id=sequence.user_id,
                    status="success" if success else "failed",
                    tracking_id=tracking_id,
                    sequence_step_id=step.id,
                )
                db.add(log)

                if success:
                    deduct_credits(
                        db, sequence.user_id, CREDIT_COSTS["email"],
                        f"시퀀스 이메일 발송: {prospect.email}",
                    )

                enrollment.last_step_sent_at = now

                # Move to next step
                next_step = (
                    db.query(EmailSequenceStep)
                    .filter(
                        EmailSequenceStep.sequence_id == sequence.id,
                        EmailSequenceStep.step_number == enrollment.current_step + 1,
                    )
                    .first()
                )
                if next_step:
                    enrollment.current_step += 1
                    enrollment.next_send_at = now + timedelta(days=next_step.delay_days)
                else:
                    enrollment.status = "completed"
            except Exception as e:
                logger.error(f"Error sending sequence email for enrollment {enrollment.id}: {e}")

        db.commit()
    except Exception as e:
        logger.error(f"Error in process_sequences job: {e}")
        db.rollback()
    finally:
        db.close()


def compute_benchmarks_job():
    """Compute industry benchmarks from email performance data."""
    db = SessionLocal()
    try:
        from app.services.benchmark import compute_benchmarks
        compute_benchmarks(db)
        db.commit()
    except Exception as e:
        logger.error(f"Error in compute_benchmarks job: {e}")
        db.rollback()
    finally:
        db.close()


def compute_keyword_performances_job():
    """Compute keyword ROI metrics."""
    db = SessionLocal()
    try:
        from app.services.roi import compute_keyword_performances
        compute_keyword_performances(db)
        db.commit()
    except Exception as e:
        logger.error(f"Error in compute_keyword_performances job: {e}")
        db.rollback()
    finally:
        db.close()


def process_replies():
    """Gmail IMAP으로 답장을 감지해 잠재고객 상태 갱신 + 시퀀스 중단."""
    db = SessionLocal()
    try:
        from app.services.reply_detector import detect_replies_all_users
        detect_replies_all_users(db)
    except Exception as e:
        logger.error(f"Error in process_replies job: {e}")
        db.rollback()
    finally:
        db.close()


def process_bounces():
    """Gmail IMAP으로 반송(바운스) 메일을 감지해 재발송 차단 + 하드바운스 크레딧 환불."""
    db = SessionLocal()
    try:
        from app.services.bounce_detector import detect_bounces_all_users
        detect_bounces_all_users(db)
    except Exception as e:
        logger.error(f"Error in process_bounces job: {e}")
        db.rollback()
    finally:
        db.close()


def process_meeting_reminders():
    """24시간 이내 미팅에 리마인더 발송."""
    db = SessionLocal()
    try:
        from app.services.meeting_notify import send_due_reminders
        send_due_reminders(db)
    except Exception as e:
        logger.error(f"Error in process_meeting_reminders job: {e}")
        db.rollback()
    finally:
        db.close()


def reap_stale_jobs_job():
    """장시간 running으로 멈춘 작업 주기 정리 (hang 방지)."""
    db = SessionLocal()
    try:
        from app.core.job_reaper import reap_stale_jobs
        reap_stale_jobs(db, startup=False)
    except Exception as e:
        logger.error(f"Error in reap_stale_jobs job: {e}")
        db.rollback()
    finally:
        db.close()


def process_scheduled_emails():
    """Check for scheduled email sends and trigger them when due."""
    db = SessionLocal()
    try:
        from app.models.models import EmailSendJob
        now = datetime.now(timezone.utc)
        jobs = db.query(EmailSendJob).filter(
            EmailSendJob.status == "scheduled",
            EmailSendJob.scheduled_at <= now,
        ).all()
        for job in jobs:
            job.status = "running"
            db.commit()
            # Trigger email sending in background thread
            import threading
            from app.api.email_send import _run_email_sending_in_background
            thread = threading.Thread(
                target=_run_email_sending_in_background,
                args=(job.project_id, job.user_id),
                daemon=True,
            )
            thread.start()
    except Exception as e:
        logger.error(f"Error in process_scheduled_emails: {e}")
        db.rollback()
    finally:
        db.close()


def start_scheduler():
    """Start the background scheduler."""
    scheduler.add_job(expire_trials, "cron", hour=0, minute=5, id="expire_trials", replace_existing=True)
    scheduler.add_job(process_sequences, "interval", minutes=15, id="process_sequences", replace_existing=True)
    scheduler.add_job(compute_benchmarks_job, "cron", hour=3, minute=0, id="compute_benchmarks", replace_existing=True)
    scheduler.add_job(compute_keyword_performances_job, "interval", hours=1, id="compute_keyword_perf", replace_existing=True)
    scheduler.add_job(process_scheduled_emails, "interval", minutes=1, id="process_scheduled_emails", replace_existing=True)
    scheduler.add_job(process_replies, "interval", minutes=15, id="process_replies", replace_existing=True)
    scheduler.add_job(reap_stale_jobs_job, "interval", minutes=30, id="reap_stale_jobs", replace_existing=True)
    scheduler.add_job(process_meeting_reminders, "interval", hours=1, id="meeting_reminders", replace_existing=True)
    scheduler.add_job(process_bounces, "interval", minutes=30, id="process_bounces", replace_existing=True)
    scheduler.start()
    logger.info("Background scheduler started")


def stop_scheduler():
    """Stop the background scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped")
