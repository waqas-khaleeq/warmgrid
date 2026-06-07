import asyncio
import json
import random
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal

scheduler = AsyncIOScheduler()


async def _get_setting(db: AsyncSession, key: str, default: str = "") -> str:
    from models import AppSettings
    result = await db.execute(select(AppSettings).where(AppSettings.setting_key == key))
    row = result.scalar_one_or_none()
    return row.setting_value if row else default


async def _log(db: AsyncSession, level: str, action: str, message: str, mailbox_id: int = None, mailbox_email: str = None, details: dict = None):
    from models import ActivityLog
    log = ActivityLog(
        level=level,
        mailbox_id=mailbox_id,
        mailbox_email=mailbox_email,
        action=action,
        message=message,
        details=json.dumps(details) if details else None,
        created_at=datetime.utcnow(),
    )
    db.add(log)
    try:
        await db.flush()
    except Exception:
        pass


async def run_daily_warmup_sends():
    async with AsyncSessionLocal() as db:
        try:
            from models import SenderMailbox, SeedMailbox, WarmupEmail
            from content_engine import generate_email_content
            from smtp_sender import send_warmup_email

            await _log(db, "info", "warmup_job_start", "Daily warmup send job started")

            send_hour_start = int(await _get_setting(db, "send_hour_start", "7"))
            send_hour_end = int(await _get_setting(db, "send_hour_end", "11"))
            min_delay = int(await _get_setting(db, "min_delay_between_sends_seconds", "60"))
            max_delay = int(await _get_setting(db, "max_delay_between_sends_seconds", "300"))
            min_seeds = int(await _get_setting(db, "min_seeds_per_send", "5"))
            max_seeds = int(await _get_setting(db, "max_seeds_per_send", "8"))

            now = datetime.utcnow()
            if not (send_hour_start <= now.hour < send_hour_end):
                await _log(db, "info", "warmup_job_skip", f"Outside send window ({send_hour_start}-{send_hour_end}), skipping")
                await db.commit()
                return

            result = await db.execute(
                select(SenderMailbox).where(SenderMailbox.is_active == True, SenderMailbox.is_paused == False)
            )
            sender_mailboxes = result.scalars().all()

            seeds_result = await db.execute(
                select(SeedMailbox).where(SeedMailbox.is_active == True)
            )
            all_seeds = seeds_result.scalars().all()

            if not all_seeds:
                await _log(db, "warning", "warmup_job_no_seeds", "No active seed mailboxes found")
                await db.commit()
                return

            total_sent = 0
            total_failed = 0

            for mailbox in sender_mailboxes:
                try:
                    volume = min(mailbox.current_daily_volume, len(all_seeds))
                    num_seeds = min(random.randint(min_seeds, max_seeds), volume)
                    selected_seeds = random.sample(all_seeds, min(num_seeds, len(all_seeds)))

                    for seed in selected_seeds:
                        try:
                            sender_name = mailbox.display_name or mailbox.email.split("@")[0]
                            content = await generate_email_content(
                                db, mailbox.id, sender_name, seed.id
                            )

                            result_send = await send_warmup_email(mailbox, seed, content["subject"], content["body"], db)

                            warmup_email = WarmupEmail(
                                sender_mailbox_id=mailbox.id,
                                seed_mailbox_id=seed.id,
                                message_id=result_send.get("message_id"),
                                subject=content["subject"],
                                body_preview=content["body"][:200],
                                sent_at=datetime.utcnow() if result_send["success"] else None,
                                status="sent" if result_send["success"] else "failed",
                            )
                            db.add(warmup_email)
                            await db.flush()

                            if result_send["success"]:
                                total_sent += 1
                                seed.last_used = datetime.utcnow()
                            else:
                                total_failed += 1

                            delay = random.uniform(min_delay, max_delay)
                            await asyncio.sleep(delay)

                        except Exception as e:
                            total_failed += 1
                            await _log(db, "error", "warmup_send_error",
                                       f"Error sending to {seed.email}: {str(e)}",
                                       mailbox_id=mailbox.id, mailbox_email=mailbox.email)

                except Exception as e:
                    await _log(db, "error", "warmup_mailbox_error",
                               f"Error processing mailbox {mailbox.email}: {str(e)}",
                               mailbox_id=mailbox.id, mailbox_email=mailbox.email)

            await _log(db, "success", "warmup_job_complete",
                       f"Daily warmup complete: {total_sent} sent, {total_failed} failed",
                       details={"sent": total_sent, "failed": total_failed})
            await db.commit()

        except Exception as e:
            await _log(db, "error", "warmup_job_error", f"Warmup job crashed: {str(e)}")
            try:
                await db.commit()
            except Exception:
                pass


async def run_imap_checks():
    async with AsyncSessionLocal() as db:
        try:
            from models import SeedMailbox, SenderMailbox, WarmupEmail
            from imap_listener import check_inbox_for_warmup_emails, rescue_from_spam, send_auto_reply
            from content_engine import generate_reply_content

            await _log(db, "info", "imap_job_start", "IMAP check job started")

            seeds_result = await db.execute(select(SeedMailbox).where(SeedMailbox.is_active == True))
            seeds = seeds_result.scalars().all()

            senders_result = await db.execute(select(SenderMailbox).where(SenderMailbox.is_active == True))
            senders = senders_result.scalars().all()
            sender_emails = [s.email for s in senders]

            content_mode = await _get_setting(db, "content_mode", "templates")
            api_key_enc = await _get_setting(db, "deepseek_api_key", "")
            api_key = ""
            if api_key_enc:
                try:
                    from config import settings
                    api_key = settings.decrypt(api_key_enc)
                except Exception:
                    pass

            total_received = 0
            total_replied = 0
            total_rescued = 0

            for seed in seeds:
                try:
                    await asyncio.sleep(30)

                    found_emails = await check_inbox_for_warmup_emails(seed, sender_emails)
                    for found in found_emails:
                        try:
                            result = await db.execute(
                                select(WarmupEmail).where(WarmupEmail.message_id == found["message_id"])
                            )
                            warmup_email = result.scalar_one_or_none()
                            if warmup_email:
                                warmup_email.received_at = found["received_at"] or datetime.utcnow()
                                warmup_email.status = "delivered"
                                await db.flush()

                            replied = await send_auto_reply(seed, found)
                            if replied and warmup_email:
                                warmup_email.replied_at = datetime.utcnow()
                                warmup_email.reply_received = True
                                warmup_email.status = "replied"
                                seed.replies_sent_total = (seed.replies_sent_total or 0) + 1
                                await db.flush()
                                total_replied += 1

                            seed.emails_received_total = (seed.emails_received_total or 0) + 1
                            total_received += 1

                        except Exception as e:
                            await _log(db, "error", "imap_process_error", f"Error processing email: {str(e)}")

                    rescued = await rescue_from_spam(seed, sender_emails)
                    if rescued > 0:
                        seed.spam_rescues_total = (seed.spam_rescues_total or 0) + rescued
                        total_rescued += rescued

                        emails_result = await db.execute(
                            select(WarmupEmail).where(
                                WarmupEmail.seed_mailbox_id == seed.id,
                                WarmupEmail.status == "sent",
                            )
                        )
                        recent_emails = emails_result.scalars().all()
                        for we in recent_emails[:rescued]:
                            we.found_in_spam = True
                            we.rescued_from_spam = True
                        await db.flush()

                except Exception as e:
                    await _log(db, "error", "imap_seed_error",
                               f"Error checking seed {seed.email}: {str(e)}")

            await _log(db, "success", "imap_job_complete",
                       f"IMAP check complete: {total_received} received, {total_replied} replied, {total_rescued} rescued",
                       details={"received": total_received, "replied": total_replied, "rescued": total_rescued})
            await db.commit()

        except Exception as e:
            await _log(db, "error", "imap_job_error", f"IMAP job crashed: {str(e)}")
            try:
                await db.commit()
            except Exception:
                pass


async def run_weekly_volume_increase():
    async with AsyncSessionLocal() as db:
        try:
            from models import SenderMailbox

            weekly_increase = int(await _get_setting(db, "weekly_volume_increase", "5"))
            max_volume = int(await _get_setting(db, "max_daily_volume", "50"))

            result = await db.execute(
                select(SenderMailbox).where(SenderMailbox.is_active == True, SenderMailbox.is_paused == False)
            )
            mailboxes = result.scalars().all()

            for mailbox in mailboxes:
                try:
                    if mailbox.current_daily_volume < mailbox.target_daily_volume:
                        new_volume = min(
                            mailbox.current_daily_volume + weekly_increase,
                            mailbox.target_daily_volume,
                            max_volume,
                        )
                        old_volume = mailbox.current_daily_volume
                        mailbox.current_daily_volume = new_volume
                        mailbox.warmup_week = (mailbox.warmup_week or 1) + 1
                        await db.flush()

                        await _log(db, "info", "volume_increase",
                                   f"Volume increased from {old_volume} to {new_volume}",
                                   mailbox_id=mailbox.id, mailbox_email=mailbox.email,
                                   details={"old_volume": old_volume, "new_volume": new_volume, "week": mailbox.warmup_week})
                except Exception as e:
                    await _log(db, "error", "volume_increase_error",
                               f"Error updating volume for {mailbox.email}: {str(e)}",
                               mailbox_id=mailbox.id, mailbox_email=mailbox.email)

            await db.commit()

        except Exception as e:
            await _log(db, "error", "volume_job_error", f"Volume increase job crashed: {str(e)}")
            try:
                await db.commit()
            except Exception:
                pass


async def run_health_checks():
    async with AsyncSessionLocal() as db:
        try:
            from models import SenderMailbox, WarmupEmail
            from health_monitor import calculate_health_score, save_health_log
            from imap_listener import check_sender_bounces
            from blacklist_checker import check_domain

            auto_pause_threshold = float(await _get_setting(db, "auto_pause_health_threshold", "50"))

            result = await db.execute(select(SenderMailbox).where(SenderMailbox.is_active == True))
            mailboxes = result.scalars().all()

            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

            for mailbox in mailboxes:
                try:
                    total_sent_result = await db.execute(
                        select(func.count(WarmupEmail.id)).where(
                            WarmupEmail.sender_mailbox_id == mailbox.id,
                            WarmupEmail.status != "failed",
                        )
                    )
                    total_sent = total_sent_result.scalar() or 0

                    spam_result = await db.execute(
                        select(func.count(WarmupEmail.id)).where(
                            WarmupEmail.sender_mailbox_id == mailbox.id,
                            WarmupEmail.found_in_spam == True,
                        )
                    )
                    spam_count = spam_result.scalar() or 0

                    reply_result = await db.execute(
                        select(func.count(WarmupEmail.id)).where(
                            WarmupEmail.sender_mailbox_id == mailbox.id,
                            WarmupEmail.reply_received == True,
                        )
                    )
                    reply_count = reply_result.scalar() or 0

                    sent_today_result = await db.execute(
                        select(func.count(WarmupEmail.id)).where(
                            WarmupEmail.sender_mailbox_id == mailbox.id,
                            WarmupEmail.sent_at >= today_start,
                        )
                    )
                    sent_today = sent_today_result.scalar() or 0

                    received_today_result = await db.execute(
                        select(func.count(WarmupEmail.id)).where(
                            WarmupEmail.sender_mailbox_id == mailbox.id,
                            WarmupEmail.received_at >= today_start,
                        )
                    )
                    received_today = received_today_result.scalar() or 0

                    rescued_today_result = await db.execute(
                        select(func.count(WarmupEmail.id)).where(
                            WarmupEmail.sender_mailbox_id == mailbox.id,
                            WarmupEmail.rescued_from_spam == True,
                            WarmupEmail.sent_at >= today_start,
                        )
                    )
                    rescued_today = rescued_today_result.scalar() or 0

                    spam_rate = (spam_count / total_sent * 100) if total_sent > 0 else 0.0
                    reply_rate = (reply_count / total_sent * 100) if total_sent > 0 else 0.0

                    bounce_count = await check_sender_bounces(mailbox)
                    bounce_rate = (bounce_count / max(total_sent, 1)) * 100

                    bl_result = await check_domain(mailbox.domain)
                    blacklisted = bl_result["is_blacklisted"]
                    blacklist_details = json.dumps(bl_result["blacklists_found_on"]) if blacklisted else None

                    health_score = await calculate_health_score(
                        db, mailbox, spam_rate, reply_rate, bounce_rate, blacklisted
                    )

                    await save_health_log(
                        db, mailbox.id, health_score, spam_rate, reply_rate, bounce_rate,
                        sent_today, received_today, rescued_today, blacklisted, blacklist_details
                    )

                    if health_score < auto_pause_threshold and not mailbox.is_paused:
                        mailbox.is_paused = True
                        await _log(db, "warning", "auto_pause",
                                   f"Mailbox auto-paused due to low health score: {health_score:.1f}",
                                   mailbox_id=mailbox.id, mailbox_email=mailbox.email,
                                   details={"health_score": health_score, "threshold": auto_pause_threshold})

                    await db.flush()

                except Exception as e:
                    await _log(db, "error", "health_check_error",
                               f"Health check failed for {mailbox.email}: {str(e)}",
                               mailbox_id=mailbox.id, mailbox_email=mailbox.email)

            await db.commit()

        except Exception as e:
            await _log(db, "error", "health_job_error", f"Health check job crashed: {str(e)}")
            try:
                await db.commit()
            except Exception:
                pass


async def run_blacklist_checks():
    async with AsyncSessionLocal() as db:
        try:
            from models import SenderMailbox
            from blacklist_checker import check_domain

            result = await db.execute(select(SenderMailbox).where(SenderMailbox.is_active == True))
            mailboxes = result.scalars().all()

            for mailbox in mailboxes:
                try:
                    bl_result = await check_domain(mailbox.domain)
                    if bl_result["is_blacklisted"]:
                        await _log(db, "warning", "blacklist_detected",
                                   f"Domain {mailbox.domain} found on blacklists: {bl_result['blacklists_found_on']}",
                                   mailbox_id=mailbox.id, mailbox_email=mailbox.email,
                                   details=bl_result)
                    else:
                        await _log(db, "info", "blacklist_clear",
                                   f"Domain {mailbox.domain} is not blacklisted",
                                   mailbox_id=mailbox.id, mailbox_email=mailbox.email)
                except Exception as e:
                    await _log(db, "error", "blacklist_check_error",
                               f"Blacklist check failed for {mailbox.email}: {str(e)}",
                               mailbox_id=mailbox.id, mailbox_email=mailbox.email)

            await db.commit()

        except Exception as e:
            await _log(db, "error", "blacklist_job_error", f"Blacklist job crashed: {str(e)}")
            try:
                await db.commit()
            except Exception:
                pass


def setup_scheduler(send_hour_start: int = 7, send_hour_end: int = 11, imap_interval_minutes: int = 120, health_interval_hours: int = 24):
    scheduler.remove_all_jobs()

    send_hour = (send_hour_start + send_hour_end) // 2
    scheduler.add_job(
        run_daily_warmup_sends,
        CronTrigger(hour=send_hour, minute=random.randint(0, 59)),
        id="daily_warmup",
        replace_existing=True,
        max_instances=1,
    )

    scheduler.add_job(
        run_imap_checks,
        IntervalTrigger(minutes=imap_interval_minutes),
        id="imap_checks",
        replace_existing=True,
        max_instances=1,
    )

    scheduler.add_job(
        run_weekly_volume_increase,
        CronTrigger(day_of_week="mon", hour=8, minute=0),
        id="weekly_volume",
        replace_existing=True,
        max_instances=1,
    )

    scheduler.add_job(
        run_health_checks,
        CronTrigger(hour=6, minute=0),
        id="health_checks",
        replace_existing=True,
        max_instances=1,
    )

    scheduler.add_job(
        run_blacklist_checks,
        CronTrigger(hour=7, minute=0),
        id="blacklist_checks",
        replace_existing=True,
        max_instances=1,
    )
