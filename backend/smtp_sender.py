import asyncio
import json
import random
import time
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid

import aiosmtplib
from sqlalchemy.ext.asyncio import AsyncSession


async def _log_activity(db: AsyncSession, level: str, mailbox_id: int, mailbox_email: str, action: str, message: str, details: dict = None):
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


async def test_smtp_connection(host: str, port: int, username: str, password: str) -> dict:
    start = time.time()
    try:
        use_tls = port == 465
        smtp = aiosmtplib.SMTP(hostname=host, port=port, use_tls=use_tls, timeout=10)
        await asyncio.wait_for(smtp.connect(), timeout=10)
        if not use_tls:
            try:
                await smtp.starttls()
            except Exception:
                pass
        await smtp.login(username, password)
        await smtp.quit()
        latency_ms = int((time.time() - start) * 1000)
        return {"success": True, "error": None, "latency_ms": latency_ms}
    except aiosmtplib.SMTPAuthenticationError as e:
        return {"success": False, "error": f"Authentication failed: {str(e)}", "latency_ms": 0}
    except aiosmtplib.SMTPConnectError as e:
        return {"success": False, "error": f"Connection refused: {str(e)}", "latency_ms": 0}
    except asyncio.TimeoutError:
        return {"success": False, "error": "Connection timed out after 10 seconds", "latency_ms": 0}
    except aiosmtplib.SMTPException as e:
        return {"success": False, "error": f"SMTP error: {str(e)}", "latency_ms": 0}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}", "latency_ms": 0}


async def send_warmup_email(
    sender_mailbox,
    seed_mailbox,
    subject: str,
    body: str,
    db: AsyncSession = None,
) -> dict:
    delay = random.uniform(5, 30)
    await asyncio.sleep(delay)

    try:
        from config import settings
        smtp_password = settings.decrypt(sender_mailbox.smtp_password)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{sender_mailbox.display_name or sender_mailbox.email} <{sender_mailbox.email}>"
        msg["To"] = seed_mailbox.email
        msg["Date"] = formatdate(localtime=True)
        message_id = make_msgid(domain=sender_mailbox.domain)
        msg["Message-ID"] = message_id
        msg["MIME-Version"] = "1.0"
        msg["Reply-To"] = sender_mailbox.email
        msg.attach(MIMEText(body, "plain"))

        port = sender_mailbox.smtp_port
        use_tls = port == 465

        smtp = aiosmtplib.SMTP(
            hostname=sender_mailbox.smtp_host,
            port=port,
            use_tls=use_tls,
            timeout=30,
        )
        await asyncio.wait_for(smtp.connect(), timeout=30)
        if not use_tls:
            try:
                await smtp.starttls()
            except Exception:
                pass
        await smtp.login(sender_mailbox.smtp_username, smtp_password)
        await smtp.send_message(msg)
        await smtp.quit()

        if db:
            await _log_activity(
                db, "success", sender_mailbox.id, sender_mailbox.email,
                "send_warmup_email",
                f"Warmup email sent to {seed_mailbox.email}: {subject}",
                {"subject": subject, "to": seed_mailbox.email, "message_id": message_id},
            )

        return {"success": True, "message_id": message_id, "error": None}

    except aiosmtplib.SMTPAuthenticationError as e:
        err = f"Authentication failed: {str(e)}"
    except aiosmtplib.SMTPConnectError as e:
        err = f"Connection error: {str(e)}"
    except asyncio.TimeoutError:
        err = "SMTP connection timed out"
    except aiosmtplib.SMTPException as e:
        err = f"SMTP error: {str(e)}"
    except Exception as e:
        err = f"Unexpected error: {str(e)}"

    if db:
        await _log_activity(
            db, "error", sender_mailbox.id, sender_mailbox.email,
            "send_warmup_email_failed",
            f"Failed to send warmup email to {seed_mailbox.email}: {err}",
            {"error": err, "to": seed_mailbox.email},
        )
    return {"success": False, "message_id": None, "error": err}
