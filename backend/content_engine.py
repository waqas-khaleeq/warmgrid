import asyncio
import hashlib
import json
import random
from datetime import datetime
from typing import Optional

import httpx
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

SUBJECT_TEMPLATES = [
    "Quick question for you",
    "Following up on this",
    "Wanted to check in",
    "Re: our earlier exchange",
    "Had a thought about this",
    "One thing I wanted to mention",
    "Did you get a chance to look at this",
    "Circling back on this",
    "Touching base",
    "Just a quick note",
    "Checking in with you",
    "Thought you might find this useful",
    "Following up from last week",
    "Re: our last conversation",
    "Quick update from my end",
    "Something I wanted to share",
    "Wanted to get your thoughts",
    "Reaching out about this",
    "A few things I wanted to cover",
    "Any update on your end",
    "Hope things are going well",
    "Following up as promised",
    "Checking on the status of this",
    "Re: the discussion we had",
    "Wanted to reconnect",
    "A quick heads up",
    "Just checking in",
    "Wanted to loop you in",
    "Re: what we talked about",
    "Following up on my last message",
    "Wanted to touch base quickly",
    "Re: moving forward on this",
    "One quick thing",
    "Keeping you in the loop",
    "Wanted to get your input",
    "Re: the item we discussed",
    "Just a brief follow-up",
    "Checking in on this",
    "Wanted to share a quick update",
    "Re: next steps",
    "Had a chance to review this",
    "Following up before end of week",
    "Something worth discussing",
    "Wanted to make sure we are aligned",
    "Reconnecting on this",
    "Re: where we left off",
    "Quick check-in",
    "Wanted to bring this to your attention",
    "Following up once more",
    "Re: our ongoing discussion",
    "Thought I would reach out",
    "Wanted to confirm a few things",
    "Any thoughts on this",
    "Re: the plan we outlined",
    "Quick follow-up from my side",
    "Wanted to revisit this with you",
    "Checking back in with you",
    "Re: picking up from last time",
    "One more thing before we proceed",
    "Wanted to keep the conversation going",
]

BODY_TEMPLATES = [
    "Hi {name}, just wanted to touch base this week. Do you have a few minutes to connect? {signoff}",
    "{greeting}, hope things are going well on your end. I had a quick thought I wanted to run by you when you get a chance. {signoff}, {name}",
    "{greeting} {name}, wanted to follow up on something we discussed earlier. Would love to hear your thoughts. {signoff}",
    "Hi there, just checking in to see how things are progressing on your end. Let me know if you need anything from me. {signoff}, {name}",
    "{greeting}, I wanted to reach out and see if now is a good time to reconnect. {signoff}",
    "Hi {name}, hope your week is going smoothly. I had a quick question I wanted to ask when you have a moment. {signoff}",
    "{greeting} {name}, just a quick follow-up from our last conversation. Do you have any updates to share? {signoff}",
    "Hi, wanted to check in and see where things stand. Let me know if there is anything I can do to help move this forward. {signoff}, {name}",
    "{greeting} {name}, I was thinking about what we discussed and wanted to share a quick thought. Would be curious to hear your take. {signoff}",
    "Hi there, hope everything is going well. Just reaching out to see if you had a chance to look into this. {signoff}, {name}",
    "{greeting}, just a brief note to follow up. Let me know when you have a moment to chat. {signoff}",
    "Hi {name}, circling back on this one. Any updates from your side? {signoff}",
    "{greeting} {name}, wanted to make sure this did not fall through the cracks. Let me know if you need anything. {signoff}",
    "Hi, just checking in quickly. Would be great to reconnect this week if your schedule allows. {signoff}, {name}",
    "{greeting}, wanted to keep the conversation going from where we left off. Any thoughts on moving forward? {signoff}",
    "Hi {name}, hope things are good on your end. I had something I wanted to discuss when you get a free moment. {signoff}",
    "{greeting} {name}, just a quick note to follow up. Let me know your thoughts when you get a chance. {signoff}",
    "Hi, wanted to reach out and touch base. Do you have a few minutes sometime this week? {signoff}, {name}",
    "{greeting}, following up as I wanted to make sure we are on the same page. Let me know if you have any questions. {signoff}",
    "Hi {name}, just checking in to see if there are any updates. Feel free to let me know when you are ready to move forward. {signoff}",
    "{greeting} {name}, wanted to share a quick update from my end. Let me know if this changes anything on your side. {signoff}",
    "Hi there, hope the week is going well. Just a brief follow-up to see if you had any thoughts on this. {signoff}, {name}",
    "{greeting}, I wanted to reconnect and see how things are progressing. Do you have a moment to talk this week? {signoff}",
    "Hi {name}, just touching base to make sure nothing got lost in the shuffle. Let me know if you need anything from me. {signoff}",
    "{greeting} {name}, hope you are having a good week. Any chance you had time to look at what I sent over? {signoff}",
    "Hi, following up from my earlier message. Would love to get your input when you have a free moment. {signoff}, {name}",
    "{greeting}, just a quick check-in. Let me know if there is anything I can do to help with this. {signoff}",
    "Hi {name}, wanted to see if you had a chance to review the details. Happy to answer any questions you might have. {signoff}",
    "{greeting} {name}, reaching out to reconnect. Hope things have been going well since we last spoke. {signoff}",
    "Hi there, just wanted to send a quick note to follow up. Let me know your thoughts when you get a moment. {signoff}, {name}",
    "{greeting}, I wanted to check in and see if you are still planning to move forward with this. Just let me know. {signoff}",
    "Hi {name}, hope your week is off to a good start. I had a quick question I wanted to run by you. {signoff}",
    "{greeting} {name}, wanted to reach out and keep things moving on our end. Any updates from you? {signoff}",
    "Hi, just following up on this. Let me know when you have a moment to connect. {signoff}, {name}",
    "{greeting}, wanted to make sure I had not missed anything. Let me know if there are any next steps I should be aware of. {signoff}",
    "Hi {name}, hope all is well. Just a quick note to check in and see how things are going on your side. {signoff}",
    "{greeting} {name}, wanted to circle back and see if you had any further thoughts on this. {signoff}",
    "Hi there, checking in quickly. Would love to reconnect and compare notes when you have a chance. {signoff}, {name}",
    "{greeting}, just reaching out to follow up on our last exchange. Let me know if anything has changed. {signoff}",
    "Hi {name}, wanted to get back to you on this. Do you have time for a quick conversation this week? {signoff}",
    "{greeting} {name}, hope things are going smoothly. Just wanted to check in and see if there are any updates. {signoff}",
    "Hi, just a brief note to follow up. Let me know if this is still on your radar. {signoff}, {name}",
    "{greeting}, wanted to reconnect and see where things stand. Looking forward to hearing from you. {signoff}",
    "Hi {name}, just checking in to see if there is anything I can help with. Happy to jump on a call if needed. {signoff}",
    "{greeting} {name}, hope the week has been good so far. Wanted to touch base and see how everything is going. {signoff}",
    "Hi there, just following up to make sure we are still aligned. Let me know if anything has changed on your end. {signoff}, {name}",
    "{greeting}, wanted to send a quick note to keep in touch. Let me know if there is anything I should know about. {signoff}",
    "Hi {name}, just a quick follow-up from our earlier conversation. Any progress to report from your side? {signoff}",
    "{greeting} {name}, hope things are going well. Just reaching out to touch base and stay connected. {signoff}",
    "Hi, following up on this one more time. Let me know your thoughts whenever you get a chance. {signoff}, {name}",
    "{greeting}, checking in to see if there is anything I missed. Happy to help if you need anything. {signoff}",
    "Hi {name}, just wanted to send a brief note and reconnect. Let me know if now is a good time to catch up. {signoff}",
    "{greeting} {name}, reaching out to follow up on something from last week. Do you have a moment to chat? {signoff}",
    "Hi there, hope your week is going well. Just checking in and wanted to see if you had any updates. {signoff}, {name}",
    "{greeting}, I wanted to keep this moving and see if there is anything new on your side. Let me know. {signoff}",
    "Hi {name}, just a quick check-in to see how things are progressing. Feel free to reach out whenever you are ready. {signoff}",
    "{greeting} {name}, wanted to follow up and make sure everything is on track. Let me know if there are any issues. {signoff}",
    "Hi, just sending a quick note to stay in touch. Hope things are going well on your end. {signoff}, {name}",
    "{greeting}, wanted to touch base before the end of the week. Let me know if anything needs my attention. {signoff}",
    "Hi {name}, hope your week is wrapping up well. Just following up to make sure nothing was missed. {signoff}",
    "{greeting} {name}, just a quick follow-up. Wanted to check in and see if there is anything I can help with. {signoff}",
    "Hi there, reaching out to reconnect and see how things are going. Let me know if you have a moment to chat. {signoff}, {name}",
    "{greeting} {name}, hope this week has been treating you well. Just wanted to send a quick note and stay connected. Let me know if you have any updates. {signoff}",
    "Hi, wanted to check in one more time before the week is out. Always good to stay in touch. Let me know when you have a moment. {signoff}, {name}",
    "Hi {name}, wanted to circle back one more time. Any news to share from your side? {signoff}",
    "{greeting}, just checking in to see if you have had a chance to review this yet. No rush, just want to stay in the loop. {signoff}",
    "Hi {name}, hope things are moving along well. Just wanted to send a quick note and check in. {signoff}",
    "{greeting} {name}, touching base again to see if there are any updates. Let me know when you are free to connect. {signoff}",
    "Hi there, following up on my previous message. Happy to answer any questions or provide more context if helpful. {signoff}, {name}",
    "{greeting}, wanted to reach out and see if there is anything from my side that can help move this forward. {signoff}",
    "Hi {name}, just a brief follow-up to see how things are going. Let me know if you need anything at all. {signoff}",
    "{greeting} {name}, hope the week has been productive. Just checking in and wanted to stay connected. {signoff}",
    "Hi, following up here to see if there are any new developments. Looking forward to hearing back from you. {signoff}, {name}",
    "{greeting}, just reaching out to touch base. Let me know if there is anything worth discussing when you have a moment. {signoff}",
    "Hi {name}, wanted to reconnect and check in on this. Please do not hesitate to reach out if you need anything. {signoff}",
    "{greeting} {name}, hope everything is going smoothly. Just a quick follow-up to stay in the loop. {signoff}",
    "Hi there, just a brief check-in. Let me know when it is a good time to catch up. {signoff}, {name}",
    "{greeting}, wanted to keep the lines of communication open. Let me know if there is anything on your end I should be aware of. {signoff}",
    "Hi {name}, following up once more. Looking forward to reconnecting when you have a free moment. {signoff}",
    "{greeting} {name}, just checking in to see if there is anything I can do from my side. Let me know. {signoff}",
    "Hi, hope things are well on your end. Just reaching out to touch base and follow up on this. {signoff}, {name}",
    "{greeting}, wanted to send a quick note to check in. Let me know how things are progressing from your perspective. {signoff}",
    "Hi {name}, following up with a quick note. Would love to reconnect when the timing works for you. {signoff}",
    "{greeting} {name}, just checking in. Let me know if there are any updates I should know about. {signoff}",
    "Hi there, hope everything is going well. Just a brief follow-up to stay on your radar. {signoff}, {name}",
    "{greeting}, wanted to reach out and see if you had a chance to think this over. Happy to jump on a call. {signoff}",
    "Hi {name}, just a quick check-in from my side. Let me know when you have a moment to connect. {signoff}",
    "{greeting} {name}, wanted to follow up one more time. Please let me know if there is anything I can help with. {signoff}",
    "Hi, following up briefly. Looking forward to hearing from you when you have a chance. {signoff}, {name}",
    "{greeting}, just touching base to make sure we are still on track. Let me know if anything comes up. {signoff}",
    "Hi {name}, hope your week is going well. Wanted to check in and see if there are any updates from your side. {signoff}",
    "{greeting} {name}, just a quick note to follow up. Let me know your availability for a brief conversation. {signoff}",
    "Hi there, just checking in one more time. Happy to connect whenever the timing works for you. {signoff}, {name}",
    "{greeting}, wanted to reach out and keep this on your radar. Let me know if you have any thoughts. {signoff}",
    "Hi {name}, just following up to see if there is anything I should know about. Feel free to respond when you have a moment. {signoff}",
    "{greeting} {name}, hope things have been going well. Wanted to touch base and stay in the loop. {signoff}",
    "Hi, circling back on this. Let me know whenever you are ready to move things forward. {signoff}, {name}",
    "{greeting}, reaching out with a quick follow-up. Let me know if this is still on your radar. {signoff}",
    "Hi {name}, wanted to send a final note to check in. Looking forward to reconnecting with you soon. {signoff}",
    "{greeting} {name}, just a quick follow-up. Would love to hear your thoughts when you have a moment. {signoff}",
]

REPLY_TEMPLATES = [
    "Thanks, will get back to you shortly.",
    "Got it, appreciate you reaching out.",
    "Received, I'll follow up soon.",
    "Thanks for the note. Will circle back.",
    "Noted, I'll be in touch.",
    "Thanks, I'll review and respond.",
    "Got it. Will get back to you by end of day.",
    "Received. Will follow up soon.",
    "Thanks for reaching out. I'll respond shortly.",
    "Noted. Talk soon.",
    "Thanks, this is helpful. Will review.",
    "Got your message. Will get back to you.",
    "Thanks for the update. Will follow up.",
    "Received. I'll take a look and respond.",
    "Got it, thanks. I'll be in touch.",
    "Thanks, will review and circle back.",
    "Noted. Will be in touch shortly.",
    "Received. Thanks for the heads up.",
    "Got it. Will follow up when I have a chance.",
    "Thanks for the message. Will get back to you soon.",
    "Noted, appreciate it. Talk soon.",
    "Got it. I'll respond once I've reviewed.",
    "Thanks, will take a look at this.",
    "Received. Will connect with you shortly.",
    "Thanks for reaching out. Will follow up.",
    "Got your note. Will respond soon.",
    "Noted. I'll be back in touch.",
    "Thanks, I'll get back to you when I can.",
    "Got it. Following up shortly.",
    "Received. I'll look into this and reply.",
    "Thanks. I'll circle back with you.",
    "Got it. Will connect with you when I can.",
    "Thanks for the update. Will be in touch.",
    "Received. Looking into this now.",
    "Got it, thanks for letting me know.",
    "Noted. I'll follow up with you soon.",
    "Thanks. Will reach back out shortly.",
    "Got it. Will review and get back to you.",
    "Received. Thanks, will respond soon.",
    "Noted. Will reply once I've reviewed.",
    "Thanks. I'll get back to you shortly.",
    "Got it. Appreciate the message.",
    "Received. I'll follow up by end of week.",
    "Thanks, will look at this shortly.",
    "Got it. I'll be in touch.",
    "Noted. Will circle back soon.",
    "Thanks for the note. Will respond.",
    "Got it. Will be back in touch.",
    "Received. I'll reply when I have an update.",
    "Thanks. Talk soon.",
    "Got it. Following up with you shortly.",
    "Noted. I'll look into this.",
    "Thanks for reaching out. Will reply shortly.",
    "Got it, appreciate it.",
    "Received. Will be in touch.",
    "Thanks. I'll get back to you when I can.",
    "Got it. Will follow up soon.",
    "Noted. Appreciate the message.",
    "Thanks. Will circle back with an update.",
    "Got it. Looking forward to connecting.",
]

GREETINGS = ["Hi", "Hey", "Hello", "Good morning", "Morning", "Hi there"]
SIGNOFFS = ["Best", "Thanks", "Regards", "Cheers", "Talk soon", "Thanks again"]

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_TIMEOUT_SECONDS = 15
DEEPSEEK_MAX_RETRIES = 3

EMAIL_GENERATION_PROMPT = """
You are writing a short professional email between two business colleagues.
Requirements:
- Subject line: 3 to 7 words, natural, no hype words
- Body: exactly 2 to 3 sentences, plain text only
- Tone: {tone}
- Context: {context}
- Sender name: {sender_name}
- No marketing language
- No links, no HTML, no emojis
- Do not start with "I hope this email finds you well"
- Do not use "synergy", "leverage", "circle back", "touch base", "reaching out"
- Must end with a soft question or statement that naturally invites a reply
- Sound like a real human, not a template
Return ONLY a valid JSON object, no explanation, no markdown:
{{"subject": "...", "body": "..."}}
"""

REPLY_GENERATION_PROMPT = """
Write a very short email reply from a busy professional.
1 to 2 sentences maximum.
Casual, natural, sounds like a real quick reply.
No greetings. No sign-off. Just the reply body text.
Return only the plain text reply, nothing else.
"""

TONES = [
    "professional and brief",
    "friendly and warm",
    "casual and direct",
    "polite and concise",
    "conversational and relaxed",
]

CONTEXTS = [
    "following up on a previous conversation",
    "checking in after some time has passed",
    "reaching out to reconnect",
    "touching base on something discussed before",
    "following up on an email sent last week",
    "checking if the other person had a chance to review something",
    "reaching out as it has been a while",
    "following up after an introduction",
]


class ContentGenerationError(Exception):
    pass


def hash_content(subject: str, body: str) -> str:
    combined = f"{subject.lower().strip()}|||{body.lower().strip()}"
    return hashlib.sha256(combined.encode()).hexdigest()


async def is_duplicate(
    db: AsyncSession,
    sender_mailbox_id: int,
    subject: str,
    body: str,
    seed_mailbox_id: int,
) -> bool:
    from models import UsedContent
    content_hash = hash_content(subject, body)
    result = await db.execute(
        select(UsedContent).where(
            UsedContent.sender_mailbox_id == sender_mailbox_id,
            UsedContent.seed_mailbox_id == seed_mailbox_id,
            UsedContent.content_hash == content_hash,
        )
    )
    return result.scalar_one_or_none() is not None


async def record_used_content(
    db: AsyncSession,
    sender_mailbox_id: int,
    seed_mailbox_id: int,
    subject: str,
    body: str,
    source: str,
) -> None:
    from models import UsedContent
    from sqlalchemy.exc import IntegrityError
    content_hash = hash_content(subject, body)
    # Check first to avoid unique constraint errors
    exists = await db.execute(
        select(UsedContent).where(
            UsedContent.sender_mailbox_id == sender_mailbox_id,
            UsedContent.seed_mailbox_id == seed_mailbox_id,
            UsedContent.content_hash == content_hash,
        )
    )
    if exists.scalar_one_or_none():
        return
    record = UsedContent(
        sender_mailbox_id=sender_mailbox_id,
        seed_mailbox_id=seed_mailbox_id,
        content_hash=content_hash,
        subject_preview=subject[:60],
        body_preview=body[:100],
        content_source=source,
        used_at=datetime.utcnow(),
    )
    db.add(record)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
    except Exception:
        pass


async def get_exhaustion_stats(db: AsyncSession, sender_mailbox_id: int) -> dict:
    from models import UsedContent
    total_result = await db.execute(
        select(func.count(UsedContent.id)).where(
            UsedContent.sender_mailbox_id == sender_mailbox_id
        )
    )
    total_used = total_result.scalar() or 0

    subjects_result = await db.execute(
        select(func.count(func.distinct(UsedContent.subject_preview))).where(
            UsedContent.sender_mailbox_id == sender_mailbox_id
        )
    )
    unique_subjects = subjects_result.scalar() or 0

    bodies_result = await db.execute(
        select(func.count(func.distinct(UsedContent.body_preview))).where(
            UsedContent.sender_mailbox_id == sender_mailbox_id
        )
    )
    unique_bodies = bodies_result.scalar() or 0

    template_pool_size = len(SUBJECT_TEMPLATES) * len(BODY_TEMPLATES)
    exhaustion_percent = min(100.0, (total_used / template_pool_size) * 100) if template_pool_size > 0 else 0.0
    daily_sends_estimate = 5
    remaining = template_pool_size - total_used
    estimated_days = max(0, remaining // max(daily_sends_estimate, 1))

    return {
        "total_used": total_used,
        "unique_subjects_used": unique_subjects,
        "unique_bodies_used": unique_bodies,
        "template_pool_size": template_pool_size,
        "pool_exhaustion_percent": round(exhaustion_percent, 2),
        "estimated_days_until_reset": estimated_days,
    }


async def reset_used_content(db: AsyncSession, sender_mailbox_id: int) -> int:
    from models import UsedContent, ActivityLog
    result = await db.execute(
        select(func.count(UsedContent.id)).where(
            UsedContent.sender_mailbox_id == sender_mailbox_id
        )
    )
    count = result.scalar() or 0

    await db.execute(
        delete(UsedContent).where(UsedContent.sender_mailbox_id == sender_mailbox_id)
    )

    log = ActivityLog(
        level="info",
        mailbox_id=sender_mailbox_id,
        action="content_pool_reset",
        message=f"Content pool reset for mailbox {sender_mailbox_id}. Deleted {count} records.",
        details=json.dumps({"deleted_count": count, "reset_at": datetime.utcnow().isoformat()}),
    )
    db.add(log)
    await db.flush()
    return count


async def generate_via_deepseek(
    sender_name: str,
    api_key: str,
    max_retries: int = DEEPSEEK_MAX_RETRIES,
) -> dict:
    tone = random.choice(TONES)
    context = random.choice(CONTEXTS)
    prompt = EMAIL_GENERATION_PROMPT.format(tone=tone, context=context, sender_name=sender_name)

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=DEEPSEEK_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    DEEPSEEK_API_URL,
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={
                        "model": DEEPSEEK_MODEL,
                        "max_tokens": 200,
                        "temperature": 0.95,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                response.raise_for_status()
                data = response.json()
                raw = data["choices"][0]["message"]["content"].strip()
                raw = raw.replace("```json", "").replace("```", "").strip()
                parsed = json.loads(raw)
                if "subject" not in parsed or "body" not in parsed:
                    raise ValueError("Missing subject or body in response")
                return {"subject": parsed["subject"].strip(), "body": parsed["body"].strip(), "source": "deepseek"}
        except (httpx.TimeoutException, httpx.HTTPStatusError) as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
                continue
            raise ContentGenerationError(f"DeepSeek API failed after {max_retries} attempts: {str(e)}")
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
                continue
            raise ContentGenerationError(f"DeepSeek response parse failed: {str(e)}")

    raise ContentGenerationError("DeepSeek max retries exceeded")


async def generate_reply_via_deepseek(api_key: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=DEEPSEEK_TIMEOUT_SECONDS) as client:
            response = await client.post(
                DEEPSEEK_API_URL,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": DEEPSEEK_MODEL,
                    "max_tokens": 80,
                    "temperature": 0.9,
                    "messages": [{"role": "user", "content": REPLY_GENERATION_PROMPT}],
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return random.choice(REPLY_TEMPLATES)


def _build_template_content(sender_name: str) -> dict:
    subject = random.choice(SUBJECT_TEMPLATES)
    body_template = random.choice(BODY_TEMPLATES)
    greeting = random.choice(GREETINGS)
    signoff = random.choice(SIGNOFFS)
    body = body_template.format(name=sender_name, greeting=greeting, signoff=signoff)
    return {"subject": subject, "body": body, "source": "templates"}


async def _get_app_setting(db: AsyncSession, key: str) -> str:
    from models import AppSettings
    result = await db.execute(select(AppSettings).where(AppSettings.setting_key == key))
    row = result.scalar_one_or_none()
    return row.setting_value if row else ""


async def generate_email_content(
    db: AsyncSession,
    sender_mailbox_id: int,
    sender_name: str,
    seed_mailbox_id: int,
    max_attempts: int = 10,
) -> dict:
    try:
        content_mode = await _get_app_setting(db, "content_mode") or "templates"
        api_key_enc = await _get_app_setting(db, "deepseek_api_key")
        max_retries_str = await _get_app_setting(db, "deepseek_max_retries")
        max_retries = int(max_retries_str) if max_retries_str else 3

        api_key = ""
        if api_key_enc:
            try:
                from config import settings as app_settings
                api_key = app_settings.decrypt(api_key_enc)
            except Exception:
                api_key = ""

        if content_mode == "deepseek" and api_key:
            for attempt in range(max_attempts):
                try:
                    content = await generate_via_deepseek(sender_name, api_key, max_retries)
                    duplicate = await is_duplicate(db, sender_mailbox_id, content["subject"], content["body"], seed_mailbox_id)
                    if not duplicate:
                        await record_used_content(db, sender_mailbox_id, seed_mailbox_id, content["subject"], content["body"], "deepseek")
                        return content
                except ContentGenerationError:
                    break

        # Template mode
        stats = await get_exhaustion_stats(db, sender_mailbox_id)
        if stats["pool_exhaustion_percent"] >= 80.0:
            await reset_used_content(db, sender_mailbox_id)

        for _ in range(50):
            content = _build_template_content(sender_name)
            duplicate = await is_duplicate(db, sender_mailbox_id, content["subject"], content["body"], seed_mailbox_id)
            if not duplicate:
                await record_used_content(db, sender_mailbox_id, seed_mailbox_id, content["subject"], content["body"], "templates")
                return content

        # Pool exhausted for this seed - reset and retry
        await reset_used_content(db, sender_mailbox_id)
        content = _build_template_content(sender_name)
        await record_used_content(db, sender_mailbox_id, seed_mailbox_id, content["subject"], content["body"], "templates")
        return content

    except Exception:
        return {
            "subject": "Following up with you",
            "body": "Hi, just wanted to check in and see how things are going. Let me know if you have a moment to connect. Thanks",
            "source": "fallback",
        }


async def generate_reply_content(db: AsyncSession, content_mode: str, api_key: str = None) -> str:
    try:
        if content_mode == "deepseek" and api_key:
            return await generate_reply_via_deepseek(api_key)
        return random.choice(REPLY_TEMPLATES)
    except Exception:
        return random.choice(REPLY_TEMPLATES)
