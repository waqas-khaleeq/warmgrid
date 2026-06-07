import asyncio
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from auth import get_current_user
from database import get_db, AsyncSessionLocal
from models import SeedMailbox
from schemas import SeedMailboxCreate, SeedMailboxOut
from seed_importer import detect_provider, get_imap_settings, get_smtp_settings, parse_csv
from imap_listener import test_imap_connection
from smtp_sender import test_smtp_connection

router = APIRouter(prefix="/api/seeds", tags=["seeds"])


@router.get("", response_model=list[SeedMailboxOut])
async def list_seeds(db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(SeedMailbox).order_by(SeedMailbox.created_at.desc()))
    return result.scalars().all()


@router.post("/test-connection")
async def test_seed_connection(body: SeedMailboxCreate, _=Depends(get_current_user)):
    provider = body.provider or detect_provider(body.email)
    imap_cfg = get_imap_settings(provider)
    smtp_cfg = get_smtp_settings(provider)
    imap_result, smtp_result = await asyncio.gather(
        test_imap_connection(imap_cfg["host"], imap_cfg["port"], body.email, body.app_password),
        test_smtp_connection(smtp_cfg["host"], smtp_cfg["port"], body.email, body.app_password),
    )
    success = imap_result["success"] and smtp_result["success"]
    error = None if success else (imap_result.get("error") or smtp_result.get("error"))
    return {"success": success, "error": error, "imap": imap_result, "smtp": smtp_result}


@router.post("")
async def create_seed(body: SeedMailboxCreate, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    from config import settings

    provider = body.provider or detect_provider(body.email)
    imap_cfg = get_imap_settings(provider)
    smtp_cfg = get_smtp_settings(provider)

    imap_result, smtp_result = await asyncio.gather(
        test_imap_connection(imap_cfg["host"], imap_cfg["port"], body.email, body.app_password),
        test_smtp_connection(smtp_cfg["host"], smtp_cfg["port"], body.email, body.app_password),
    )

    if not imap_result["success"]:
        raise HTTPException(status_code=400, detail=f"IMAP connection failed: {imap_result['error']}")
    if not smtp_result["success"]:
        raise HTTPException(status_code=400, detail=f"SMTP connection failed: {smtp_result['error']}")

    existing = await db.execute(select(SeedMailbox).where(SeedMailbox.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Seed mailbox with this email already exists")

    seed = SeedMailbox(
        email=body.email,
        imap_host=imap_cfg["host"],
        imap_port=imap_cfg["port"],
        imap_username=body.email,
        app_password=settings.encrypt(body.app_password),
        smtp_host=smtp_cfg["host"],
        smtp_port=smtp_cfg["port"],
        provider=provider,
    )
    db.add(seed)
    await db.flush()
    return {
        "seed": SeedMailboxOut.model_validate(seed).model_dump(),
        "imap_test": imap_result,
        "smtp_test": smtp_result,
    }


@router.post("/import-csv")
async def import_csv(file: UploadFile = File(...), db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    from config import settings

    content = await file.read()
    parsed = parse_csv(content.decode("utf-8", errors="replace"))
    rows = parsed["rows"]
    parse_errors = parsed["errors"]

    imported = 0
    failed = 0
    errors = [{"email": e.get("email", ""), "error": e["error"]} for e in parse_errors]

    for row in rows:
        try:
            await asyncio.sleep(2)
            imap_result, smtp_result = await asyncio.gather(
                test_imap_connection(row["imap_host"], row["imap_port"], row["email"], row["app_password"]),
                test_smtp_connection(row["smtp_host"], row["smtp_port"], row["email"], row["app_password"]),
            )

            if not imap_result["success"]:
                errors.append({"email": row["email"], "error": f"IMAP: {imap_result['error']}"})
                failed += 1
                continue
            if not smtp_result["success"]:
                errors.append({"email": row["email"], "error": f"SMTP: {smtp_result['error']}"})
                failed += 1
                continue

            existing = await db.execute(select(SeedMailbox).where(SeedMailbox.email == row["email"]))
            if existing.scalar_one_or_none():
                errors.append({"email": row["email"], "error": "Already exists"})
                failed += 1
                continue

            seed = SeedMailbox(
                email=row["email"],
                imap_host=row["imap_host"],
                imap_port=row["imap_port"],
                imap_username=row["email"],
                app_password=settings.encrypt(row["app_password"]),
                smtp_host=row["smtp_host"],
                smtp_port=row["smtp_port"],
                provider=row["provider"],
            )
            db.add(seed)
            await db.flush()
            imported += 1
        except Exception as e:
            errors.append({"email": row.get("email", ""), "error": str(e)})
            failed += 1

    return {
        "total_rows": len(rows) + len(parse_errors),
        "imported": imported,
        "failed": failed + len(parse_errors),
        "errors": errors,
    }


@router.post("/import-csv-sse")
async def import_csv_sse(
    request: Request,
    file: UploadFile = File(...),
    _=Depends(get_current_user),
):
    from config import settings as app_settings

    content = await file.read()
    parsed = parse_csv(content.decode("utf-8", errors="replace"))
    rows = parsed["rows"]
    parse_errors = parsed["errors"]

    # SSE uses its own DB session — cannot share the request-scoped session
    async def event_generator():
        imported = 0
        failed = 0
        errors = []
        total = len(rows)

        yield {"data": json.dumps({"type": "start", "total": total, "parse_errors": len(parse_errors)})}

        for i, row in enumerate(rows):
            if await request.is_disconnected():
                break
            try:
                await asyncio.sleep(2)
                yield {"data": json.dumps({"type": "testing", "email": row["email"], "index": i + 1, "total": total})}

                imap_result, smtp_result = await asyncio.gather(
                    test_imap_connection(row["imap_host"], row["imap_port"], row["email"], row["app_password"]),
                    test_smtp_connection(row["smtp_host"], row["smtp_port"], row["email"], row["app_password"]),
                )

                if not imap_result["success"]:
                    err = f"IMAP: {imap_result['error']}"
                    errors.append({"email": row["email"], "error": err})
                    failed += 1
                    yield {"data": json.dumps({"type": "row_failed", "email": row["email"], "error": err})}
                    continue

                if not smtp_result["success"]:
                    err = f"SMTP: {smtp_result['error']}"
                    errors.append({"email": row["email"], "error": err})
                    failed += 1
                    yield {"data": json.dumps({"type": "row_failed", "email": row["email"], "error": err})}
                    continue

                # Use a fresh session per row to avoid shared-state issues
                async with AsyncSessionLocal() as db:
                    existing = await db.execute(select(SeedMailbox).where(SeedMailbox.email == row["email"]))
                    if existing.scalar_one_or_none():
                        err = "Already exists"
                        errors.append({"email": row["email"], "error": err})
                        failed += 1
                        yield {"data": json.dumps({"type": "row_failed", "email": row["email"], "error": err})}
                        continue

                    seed = SeedMailbox(
                        email=row["email"],
                        imap_host=row["imap_host"],
                        imap_port=row["imap_port"],
                        imap_username=row["email"],
                        app_password=app_settings.encrypt(row["app_password"]),
                        smtp_host=row["smtp_host"],
                        smtp_port=row["smtp_port"],
                        provider=row["provider"],
                    )
                    db.add(seed)
                    await db.commit()

                imported += 1
                yield {"data": json.dumps({"type": "row_success", "email": row["email"]})}

            except Exception as e:
                err = str(e)
                errors.append({"email": row.get("email", ""), "error": err})
                failed += 1
                yield {"data": json.dumps({"type": "row_failed", "email": row.get("email", ""), "error": err})}

        yield {"data": json.dumps({
            "type": "complete",
            "total_rows": total + len(parse_errors),
            "imported": imported,
            "failed": failed + len(parse_errors),
            "errors": errors,
        })}

    return EventSourceResponse(event_generator())


@router.delete("/{seed_id}")
async def delete_seed(seed_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    result = await db.execute(select(SeedMailbox).where(SeedMailbox.id == seed_id))
    seed = result.scalar_one_or_none()
    if not seed:
        raise HTTPException(status_code=404, detail="Seed not found")
    await db.delete(seed)
    await db.flush()
    return {"deleted": True}


@router.post("/{seed_id}/test")
async def test_seed(seed_id: int, db: AsyncSession = Depends(get_db), _=Depends(get_current_user)):
    from config import settings
    result = await db.execute(select(SeedMailbox).where(SeedMailbox.id == seed_id))
    seed = result.scalar_one_or_none()
    if not seed:
        raise HTTPException(status_code=404, detail="Seed not found")

    password = settings.decrypt(seed.app_password)
    imap_result, smtp_result = await asyncio.gather(
        test_imap_connection(seed.imap_host, seed.imap_port, seed.imap_username, password),
        test_smtp_connection(seed.smtp_host, seed.smtp_port, seed.imap_username, password),
    )
    return {"imap": imap_result, "smtp": smtp_result}
