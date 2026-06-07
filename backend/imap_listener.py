import asyncio
import email
import json
import random
import time
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid

import aioimaplib
import aiosmtplib
from sqlalchemy.ext.asyncio import AsyncSession

from content_engine import REPLY_TEMPLATES


async def test_imap_connection(host: str, port: int, username: str, password: str) -> dict:
    try:
        client = aioimaplib.IMAP4_SSL(host=host, port=port, timeout=10)
        await asyncio.wait_for(client.wait_hello_from_server(), timeout=10)
        response = await asyncio.wait_for(client.login(username, password), timeout=10)
        if response.result != "OK":
            await client.logout()
            return {"success": False, "error": "Authentication failed", "folder_count": 0}
        list_response = await client.list("", "*")
        folder_count = len(list_response.lines) if list_response.result == "OK" else 0
        await client.logout()
        return {"success": True, "error": None, "folder_count": folder_count}
    except asyncio.TimeoutError:
        return {"success": False, "error": "Connection timed out after 10 seconds", "folder_count": 0}
    except aioimaplib.Abort as e:
        return {"success": False, "error": f"IMAP connection aborted: {str(e)}", "folder_count": 0}
    except Exception as e:
        return {"success": False, "error": f"IMAP error: {str(e)}", "folder_count": 0}


async def check_inbox_for_warmup_emails(seed_mailbox, sender_emails_list: list) -> list:
    found = []
    try:
        from config import settings
        password = settings.decrypt(seed_mailbox.app_password)
        client = aioimaplib.IMAP4_SSL(host=seed_mailbox.imap_host, port=seed_mailbox.imap_port, timeout=30)
        await asyncio.wait_for(client.wait_hello_from_server(), timeout=10)
        await asyncio.wait_for(client.login(seed_mailbox.imap_username, password), timeout=10)
        await client.select("INBOX")

        for sender_email in sender_emails_list:
            search_resp = await client.search(f'FROM "{sender_email}"')
            if search_resp.result != "OK":
                continue
            uids_str = search_resp.lines[0].decode() if search_resp.lines else ""
            if not uids_str.strip():
                continue
            uids = uids_str.strip().split()
            for uid in uids:
                fetch_resp = await client.fetch(uid, "(RFC822)")
                if fetch_resp.result != "OK":
                    continue
                for item in fetch_resp.lines:
                    if isinstance(item, bytes) and item.startswith(b"From"):
                        continue
                    if isinstance(item, bytes) and len(item) > 100:
                        try:
                            msg = email.message_from_bytes(item)
                            message_id = msg.get("Message-ID", "")
                            subject = msg.get("Subject", "")
                            from_email = msg.get("From", "")
                            date_str = msg.get("Date", "")
                            received_at = None
                            try:
                                from email.utils import parsedate_to_datetime
                                received_at = parsedate_to_datetime(date_str) if date_str else None
                            except Exception:
                                received_at = datetime.utcnow()

                            found.append({
                                "message_id": message_id,
                                "subject": subject,
                                "from_email": sender_email,
                                "received_at": received_at,
                                "folder": "INBOX",
                                "uid": uid.decode() if isinstance(uid, bytes) else uid,
                            })
                            # Mark as SEEN and FLAGGED
                            await client.store(uid, "+FLAGS", "\\Seen \\Flagged")
                        except Exception:
                            continue

        await client.logout()
    except Exception:
        pass
    return found


async def rescue_from_spam(seed_mailbox, sender_emails_list: list) -> int:
    rescued = 0
    spam_folders = ["Spam", "Junk", "[Gmail]/Spam", "Junk Email", "SPAM"]
    try:
        from config import settings
        password = settings.decrypt(seed_mailbox.app_password)
        client = aioimaplib.IMAP4_SSL(host=seed_mailbox.imap_host, port=seed_mailbox.imap_port, timeout=30)
        await asyncio.wait_for(client.wait_hello_from_server(), timeout=10)
        await asyncio.wait_for(client.login(seed_mailbox.imap_username, password), timeout=10)

        for folder in spam_folders:
            select_resp = await client.select(folder)
            if select_resp.result != "OK":
                continue
            for sender_email in sender_emails_list:
                search_resp = await client.search(f'FROM "{sender_email}"')
                if search_resp.result != "OK":
                    continue
                uids_str = search_resp.lines[0].decode() if search_resp.lines else ""
                if not uids_str.strip():
                    continue
                uids = uids_str.strip().split()
                for uid in uids:
                    try:
                        await client.copy(uid, "INBOX")
                        await client.store(uid, "+FLAGS", "\\Deleted")
                        rescued += 1
                    except Exception:
                        continue
            try:
                await client.expunge()
            except Exception:
                pass

        await client.logout()
    except Exception:
        pass
    return rescued


async def send_auto_reply(seed_mailbox, original_email: dict) -> bool:
    try:
        from config import settings
        password = settings.decrypt(seed_mailbox.app_password)
        reply_body = random.choice(REPLY_TEMPLATES)

        original_subject = original_email.get("subject", "")
        original_from = original_email.get("from_email", "")
        original_message_id = original_email.get("message_id", "")

        msg = MIMEMultipart("alternative")
        reply_subject = f"Re: {original_subject}" if not original_subject.startswith("Re:") else original_subject
        msg["Subject"] = reply_subject
        msg["From"] = seed_mailbox.email
        msg["To"] = original_from
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid()
        if original_message_id:
            msg["In-Reply-To"] = original_message_id
            msg["References"] = original_message_id
        msg.attach(MIMEText(reply_body, "plain"))

        port = seed_mailbox.smtp_port
        use_tls = port == 465
        smtp = aiosmtplib.SMTP(hostname=seed_mailbox.smtp_host, port=port, use_tls=use_tls, timeout=30)
        await asyncio.wait_for(smtp.connect(), timeout=30)
        if not use_tls:
            try:
                await smtp.starttls()
            except Exception:
                pass
        await smtp.login(seed_mailbox.imap_username, password)
        await smtp.send_message(msg)
        await smtp.quit()
        return True
    except Exception:
        return False


async def check_sender_bounces(sender_mailbox) -> int:
    bounce_count = 0
    try:
        from config import settings
        password = settings.decrypt(sender_mailbox.imap_password)
        client = aioimaplib.IMAP4_SSL(host=sender_mailbox.imap_host, port=sender_mailbox.imap_port, timeout=30)
        await asyncio.wait_for(client.wait_hello_from_server(), timeout=10)
        await asyncio.wait_for(client.login(sender_mailbox.imap_username, password), timeout=10)
        await client.select("INBOX")

        search_resp = await client.search('FROM "mailer-daemon@"')
        if search_resp.result == "OK":
            uids_str = search_resp.lines[0].decode() if search_resp.lines else ""
            if uids_str.strip():
                bounce_count += len(uids_str.strip().split())

        search_resp2 = await client.search('SUBJECT "Delivery Status Notification"')
        if search_resp2.result == "OK":
            uids_str2 = search_resp2.lines[0].decode() if search_resp2.lines else ""
            if uids_str2.strip():
                bounce_count += len(uids_str2.strip().split())

        await client.logout()
    except Exception:
        pass
    return bounce_count
