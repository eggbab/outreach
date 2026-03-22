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

            settings = db.query(UserSettings).filter(UserSettings.user_id == sequence.user_id).first()
            if not settings or not settings.gmail_email or not settings.gmail_app_password_encrypted:
                continue

            try:
                gmail_pw = decrypt_value(settings.gmail_app_password_encrypted)
                subject = step.subject.replace("{company_name}", prospect.name or "")
                body = step.body.replace("{company_name}", prospect.name or "")

                import secrets
                tracking_id = secrets.token_hex(16)

                success = send_email(
                    gmail_email=settings.gmail_email,
                    gmail_app_password=gmail_pw,
                    to_email=prospect.email,
                    subject=subject,
                    html_body=body,
                )

                log = EmailLog(
                    prospect_id=prospect.id,
                    user_id=sequence.user_id,
                    status="success" if success else "failed",
                    tracking_id=tracking_id,
                    sequence_step_id=step.id,
                )
                db.add(log)

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


def start_scheduler():
    """Start the background scheduler."""
    scheduler.add_job(expire_trials, "cron", hour=0, minute=5, id="expire_trials", replace_existing=True)
    scheduler.add_job(process_sequences, "interval", minutes=15, id="process_sequences", replace_existing=True)
    scheduler.start()
    logger.info("Background scheduler started")


def stop_scheduler():
    """Stop the background scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped")
